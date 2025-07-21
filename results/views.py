from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.core.paginator import Paginator
import json
import csv
import io
from .models import StudentResult, ManualResultEntry, ResultQuery
from .forms import RollNumberSearchForm, ManualMarksEntryForm


def calculate_sgpa(result, subjects):
    """Calculate SGPA based on marks and credits"""
    total_points = 0
    total_credits = 0
    total_marks = 0
    
    for subject in subjects:
        code = subject['code']
        credit = subject['credit']
        
        # Skip non-credit subjects
        if credit == 0:
            continue
            
        marks = result.marks_data.get(code, {})
        theory = marks.get('theory')
        internal = marks.get('internal')
        
        if theory is not None and internal is not None:
            subject_total = theory + internal
            total_marks += subject_total
            
            # AKTU grade point mapping (10-point scale)
            if subject_total >= 90:
                grade_point = 10
            elif subject_total >= 80:
                grade_point = 9
            elif subject_total >= 70:
                grade_point = 8
            elif subject_total >= 60:
                grade_point = 7
            elif subject_total >= 50:
                grade_point = 6
            elif subject_total >= 40:
                grade_point = 5
            else:
                grade_point = 0
                
            total_points += grade_point * credit
            total_credits += credit
    
    sgpa = round(total_points / total_credits, 2) if total_credits > 0 else None
    return sgpa, total_marks


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def result_home(request):
    """Main result page with options to search or manually enter marks"""
    # Get default subjects (CSE) for the home page
    default_subjects = StudentResult.SUBJECTS_DATA
    
    context = {
        'subjects': default_subjects['subjects'],
        'semester': default_subjects['semester'],
        'branch': default_subjects['branch'],
        'college': default_subjects['college'],
        'title': 'Result Checker - 6th Semester CSE',
        'meta_description': 'Check your 6th semester CSE results from AKTU. Enter roll number or manually add marks.',
    }
    return render(request, 'results/result_home.html', context)


def search_result(request):
    """Search for result by roll number"""
    form = RollNumberSearchForm()
    result = None
    show_preview = False
    sgpa = None
    total_marks = None
    
    # Check if this is a redirect from login with a roll number
    redirect_roll_number = request.GET.get('roll_number')
    
    if request.method == 'POST':
        form = RollNumberSearchForm(request.POST)
        if form.is_valid():
            roll_number = form.cleaned_data['roll_number'].upper().strip()
            
            # Log the query
            ResultQuery.objects.create(
                roll_number=roll_number,
                user=request.user if request.user.is_authenticated else None,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                result_found=False  # Will update this below
            )
            
            try:
                result = StudentResult.objects.get(roll_number=roll_number)
                
                # Get appropriate subject data for this roll number
                subjects_data = StudentResult.get_subjects_data(result.roll_number)
                
                # Calculate SGPA and total marks
                sgpa, total_marks = calculate_sgpa(result, subjects_data['subjects'])
                
                # Update query log
                ResultQuery.objects.filter(
                    roll_number=roll_number
                ).update(result_found=True)
                
                # Show preview (partial result) to non-authenticated users
                if not request.user.is_authenticated:
                    show_preview = True
                    messages.info(request, 'Login to view complete result details.')
                
            except StudentResult.DoesNotExist:
                messages.error(request, f'No result found for roll number: {roll_number}')
    
    # Handle redirect from login with roll number
    elif redirect_roll_number and request.user.is_authenticated:
        roll_number = redirect_roll_number.upper().strip()
        try:
            result = StudentResult.objects.get(roll_number=roll_number)
            
            # Get appropriate subject data for this roll number
            subjects_data = StudentResult.get_subjects_data(result.roll_number)
            sgpa, total_marks = calculate_sgpa(result, subjects_data['subjects'])
            
            # Pre-populate the form with the roll number
            form = RollNumberSearchForm(initial={'roll_number': roll_number, 'terms_accepted': True})
            
            messages.success(request, 'Login successful! Here is your complete result.')
            
        except StudentResult.DoesNotExist:
            messages.error(request, f'No result found for roll number: {roll_number}')
    
    # Get appropriate subject data based on result (if found) or default to CSE
    if result:
        subjects_data = StudentResult.get_subjects_data(result.roll_number)
    else:
        subjects_data = StudentResult.SUBJECTS_DATA  # Default to CSE
    
    context = {
        'form': form,
        'result': result,
        'show_preview': show_preview,
        'subjects': subjects_data['subjects'],
        'sgpa': sgpa,
        'total_marks': total_marks,
        'subjects_json': json.dumps(subjects_data['subjects']),
        'marks_json': json.dumps(result.marks_data) if result else '{}',
        'result_json': json.dumps({
            'roll_number': result.roll_number,
            'name': result.name,
            'father_name': result.father_name,
            'sgpa': str(sgpa) if sgpa else 'N/A',
            'total_marks': str(total_marks) if total_marks else 'N/A'
        }) if result else '{}',
        'title': 'Search Result by Roll Number',
        'meta_description': 'Search for your 6th semester CSE result using your roll number.',
    }
    return render(request, 'results/search_result.html', context)


def manual_entry(request):
    """Manual marks entry form"""
    if request.method == 'POST':
        form = ManualMarksEntryForm(request.POST)
        if form.is_valid():
            manual_entry = form.save(commit=False)
            if request.user.is_authenticated:
                manual_entry.user = request.user
            manual_entry.marks_data = form.cleaned_data['marks_data']
            manual_entry.save()
            
            messages.success(request, 'Marks saved successfully!')
            return redirect('results:view_manual_result', pk=manual_entry.pk)
    else:
        form = ManualMarksEntryForm()
    
    context = {
        'form': form,
        'subjects': StudentResult.SUBJECTS_DATA['subjects'],
        'title': 'Manual Marks Entry',
        'meta_description': 'Manually enter your marks for 6th semester CSE subjects.',
    }
    print(context)
    return render(request, 'results/manual_entry.html', context)


def view_manual_result(request, pk):
    """View manually entered result"""
    manual_result = get_object_or_404(ManualResultEntry, pk=pk)
    
    # Check if user has permission to view this result
    if not request.user.is_authenticated and manual_result.user:
        messages.error(request, 'You need to login to view this result.')
        return redirect('results:search_result')
    
    context = {
        'result': manual_result,
        'subjects': StudentResult.SUBJECTS_DATA['subjects'],
        'title': f'Result for {manual_result.roll_number}',
        'meta_description': f'View result for roll number {manual_result.roll_number}',
    }
    return render(request, 'results/view_result.html', context)


@login_required
def view_full_result(request, roll_number):
    """View full result details (authenticated users only)"""
    result = get_object_or_404(StudentResult, roll_number=roll_number)
    
    context = {
        'result': result,
        'subjects': StudentResult.SUBJECTS_DATA['subjects'],
        'show_full': True,
        'title': f'Full Result - {result.name}',
        'meta_description': f'Complete result details for {result.name} - {roll_number}',
    }
    return render(request, 'results/view_result.html', context)


@method_decorator(csrf_exempt, name='dispatch')
class BulkUploadView(View):
    """View for bulk uploading results from CSV"""
    
    def get(self, request):
        context = {
            'title': 'Bulk Upload Results',
            'meta_description': 'Upload results in bulk from CSV file.',
        }
        return render(request, 'results/bulk_upload.html', context)
    
    def post(self, request):
        if not request.user.is_staff:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        if 'csv_file' not in request.FILES:
            return JsonResponse({'error': 'No file uploaded'}, status=400)
        
        csv_file = request.FILES['csv_file']
        
        try:
            # Read CSV file
            decoded_file = csv_file.read().decode('utf-8')
            csv_data = csv.reader(io.StringIO(decoded_file))
            
            created_count = 0
            updated_count = 0
            
            for row in csv_data:
                if len(row) >= 4:  # roll_number, name, father_name, marks_data
                    roll_number = row[0].strip()
                    name = row[1].strip()
                    father_name = row[2].strip()
                    marks_data_str = row[3]
                    
                    try:
                        # Parse marks data from string representation
                        marks_data = eval(marks_data_str)  # Be careful with eval in production
                        
                        # Create or update student result
                        result, created = StudentResult.objects.get_or_create(
                            roll_number=roll_number,
                            defaults={
                                'name': name,
                                'father_name': father_name,
                            }
                        )
                        
                        # Parse and save marks
                        parsed_marks = result.parse_marks_from_raw_data(marks_data)
                        result.marks_data = parsed_marks
                        result.save()
                        
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                            
                    except Exception as e:
                        continue  # Skip invalid rows
            
            return JsonResponse({
                'success': True,
                'created': created_count,
                'updated': updated_count
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


def result_statistics(request):
    """View result statistics"""
    context = {
        'total_results': StudentResult.objects.count(),
        'total_queries': ResultQuery.objects.count(),
        'manual_entries': ManualResultEntry.objects.count(),
        'recent_queries': ResultQuery.objects.order_by('-timestamp')[:10],
        'title': 'Result Statistics',
        'meta_description': 'Statistics and analytics for result queries.',
    }
    return render(request, 'results/statistics.html', context)
