from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.core.paginator import Paginator
from django.forms import formset_factory, Form, CharField, IntegerField, FloatField, BooleanField
import json
import csv
import io
from django.templatetags.static import static
from core.models import SEODetail
from .models import StudentResult, ManualResultEntry, ResultQuery
from .forms import RollNumberSearchForm, ManualMarksEntryForm


def get_8th_sem_subjects_v2():
    return [
        {"code": "BT-801", "name": "Rural Development: Administration and Planning", "credit": 3, "max_marks": 150},
        {"code": "BT-816", "name": "Cloud Computing", "credit": 3, "max_marks": 150},
        {"code": "BT-817", "name": "Data Warehousing & Data Mining", "credit": 3, "max_marks": 150},
        {"code": "BT-866", "name": "Project", "credit": 9, "max_marks": 400}
    ]


def get_8th_sem_cse_subjects_v2():
    return [
        {"code": "BT-801", "name": "Rural Development: Administration and Planning", "credit": 3, "max_marks": 150},
        {"code": "BT-811", "name": "Natural Language Processing", "credit": 3, "max_marks": 150},
        {"code": "BT-812", "name": "Big Data", "credit": 3, "max_marks": 150},
        {"code": "BT-861", "name": "Project", "credit": 9, "max_marks": 400}
    ]


def get_4th_sem_csit_subjects_v2():
    return [
        {"code": "BT-405", "name": "Mathematics - IV", "credit": 4, "max_marks": 100},
        {"code": "BT-406", "name": "Operating Systems", "credit": 4, "max_marks": 100},
        {"code": "BT-407", "name": "Theory of Automata and Formal Languages", "credit": 4, "max_marks": 100},
        {"code": "BT-408", "name": "Object Oriented Programming with Java", "credit": 3, "max_marks": 100},
        {"code": "BT-410", "name": "Python Programming", "credit": 2, "max_marks": 100},
        {"code": "BT-414", "name": "Universal Human Values", "credit": 3, "max_marks": 100},
        {"code": "BT-454", "name": "Sports and Yoga - II", "credit": 0, "max_marks": 100},
        {"code": "BT-456", "name": "Operating Systems Lab", "credit": 1, "max_marks": 100},
        {"code": "BT-458", "name": "Object Oriented Programming with Java Lab", "credit": 1, "max_marks": 100},
        {"code": "BT-459", "name": "Cyber Security Workshop", "credit": 1, "max_marks": 100},
    ]

def get_grade_point_by_percentage(percent):
    if percent >= 90:
        return 10
    elif percent >= 80:
        return 9
    elif percent >= 70:
        return 8
    elif percent >= 60:
        return 7
    elif percent >= 50:
        return 6
    elif percent >= 40:
        return 5
    else:
        return 0


def get_subjects_data_by_roll(roll_number):
    try:
        roll_int = int(roll_number)
        if 100210500 <= roll_int <= 100210600:
            return {
                "semester": "8th",
                "branch": "IT",
                "college": "SCRIET",
                "subjects": get_8th_sem_subjects_v2()
            }
        elif 100210100 <= roll_int <= 100210200:
            return {
                "semester": "8th",
                "branch": "CS",
                "college": "SCRIET",
                "subjects": get_8th_sem_cse_subjects_v2()
            }
        elif 100230500 <= roll_int <= 100230600:
            return {
                "semester": "4th",
                "branch": "IT",
                "college": "SCRIET",
                "subjects": get_4th_sem_csit_subjects_v2()
            }
        elif 100230100 <= roll_int <= 100230200:
            return {
                "semester": "4th",
                "branch": "CS",
                "college": "SCRIET",
                "subjects": get_4th_sem_csit_subjects_v2()
            }
        elif 100220500 <= roll_int <= 100220600:
            # IT 6th sem
            return StudentResult.IT_SUBJECTS_DATA
        else:
            return StudentResult.SUBJECTS_DATA
    except Exception:
        return StudentResult.SUBJECTS_DATA


def calculate_sgpa(result, subjects):
    """Calculate SGPA based on marks and credits, with 8th sem IT support"""
    total_points = 0
    total_credits = 0
    total_marks = 0
    roll_number = getattr(result, 'roll_number', None)
    is_8th_it = False
    try:
        roll_int = int(roll_number)
        if 100210500 <= roll_int <= 100210600:
            is_8th_it = True
        if 100210100 <= roll_int <= 100210200:
            is_8th_it = True
    except Exception:
        pass

    for subject in subjects:
        code = subject['code']
        credit = subject['credit']
        max_marks = subject.get('max_marks', 100)
        if credit == 0:
            continue
        marks = result.marks_data.get(code, {})
        theory = marks.get('theory')
        internal = marks.get('internal')
        if theory is not None and internal is not None:
            subject_total = theory + internal
            total_marks += subject_total
            if is_8th_it:
                percent = (subject_total / max_marks) * 100 if max_marks else 0
                grade_point = get_grade_point_by_percentage(percent)
            else:
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
    seo_detail = SEODetail.objects.filter(page_name="search_result").first()
    if not seo_detail:
        seo_detail = SEODetail(
            title="Check Out You SGPA - Gyan Aangan",
            meta_description="Check Out your SGPA NOW at GYAN AANGAN CALCULATOR",
            og_image=None,
            site_name="Gyan Aangan",
        )
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
                
                # 15 second delay for loading experience
                import time
                time.sleep(10)
                
                # Get appropriate subject data for this roll number
                subjects_data = get_subjects_data_by_roll(result.roll_number)
                print(subjects_data)
                
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
            
            # Log the query for authenticated user redirect
            ResultQuery.objects.create(
                roll_number=roll_number,
                user=request.user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                result_found=True
            )
            
            # 15 second delay for loading experience
            import time
            time.sleep(8)
            
            # Get appropriate subject data for this roll number
            subjects_data = get_subjects_data_by_roll(result.roll_number)
            sgpa, total_marks = calculate_sgpa(result, subjects_data['subjects'])
            
            # Pre-populate the form with the roll number
            form = RollNumberSearchForm(initial={'roll_number': roll_number, 'terms_accepted': True})
            
            messages.success(request, 'Login successful! Here is your complete result.')
            
        except StudentResult.DoesNotExist:
            # Log the query even if result is not found
            ResultQuery.objects.create(
                roll_number=roll_number,
                user=request.user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                result_found=False
            )
            messages.error(request, f'No result found for roll number: {roll_number}')
    
    # Get appropriate subject data based on result (if found) or default to CSE
    if result:
        subjects_data = get_subjects_data_by_roll(result.roll_number)
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
        "title": seo_detail.title,
        "meta_description": seo_detail.meta_description,
        "og_image": (
            seo_detail.og_image.url
            if seo_detail.og_image
            else static("images/default-og-image.jpg")
        ),
        "site_name": seo_detail.site_name,
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


class ManualSubjectForm(Form):
    subject_name = CharField(max_length=100, label="Subject Name")
    marks_obtained = IntegerField(label="Marks Obtained", required=False)
    theory_marks = IntegerField(label="Theory Marks", required=False)
    internal_marks = IntegerField(label="Internal Marks", required=False)
    use_theory_internal = BooleanField(label="Enter Theory & Internal Separately?", required=False)
    total_marks = IntegerField(label="Total Marks")
    credit = FloatField(label="Credit")

def manual_calculator(request):
    ManualSubjectFormSet = formset_factory(ManualSubjectForm, extra=1, min_num=1, validate_min=True)
    result = None
    sgpa = None
    total_marks = None
    subjects_data = []
    show_result = False
    show_full = request.user.is_authenticated
    error = None

    if request.method == 'POST':
        formset = ManualSubjectFormSet(request.POST)
        if formset.is_valid():
            subjects = []
            total_points = 0
            total_credits = 0
            total_marks = 0
            max_total_marks = 0
            for form in formset:
                name = form.cleaned_data['subject_name']
                credit = form.cleaned_data['credit']
                use_theory_internal = form.cleaned_data.get('use_theory_internal', False)
                if use_theory_internal:
                    theory = form.cleaned_data.get('theory_marks') or 0
                    internal = form.cleaned_data.get('internal_marks') or 0
                    marks = theory + internal
                else:
                    marks = form.cleaned_data.get('marks_obtained') or 0
                    theory = None
                    internal = None
                max_marks = form.cleaned_data['total_marks']
                percent = (marks / max_marks) * 100 if max_marks else 0
                # AKTU 10-point scale
                if percent >= 90:
                    grade_point = 10
                elif percent >= 80:
                    grade_point = 9
                elif percent >= 70:
                    grade_point = 8
                elif percent >= 60:
                    grade_point = 7
                elif percent >= 50:
                    grade_point = 6
                elif percent >= 40:
                    grade_point = 5
                else:
                    grade_point = 0
                total_points += grade_point * credit
                total_credits += credit
                total_marks += marks
                max_total_marks += max_marks
                subjects.append({
                    'name': name,
                    'marks': marks,
                    'theory': theory,
                    'internal': internal,
                    'total_marks': max_marks,
                    'credit': credit,
                    'percent': percent,
                    'grade_point': grade_point,
                })
            sgpa = round(total_points / total_credits, 2) if total_credits > 0 else None
            show_result = True
            subjects_data = subjects

            # Save manual entry for user only if logged in
            if request.user.is_authenticated:
                from .models import ManualResultEntry
                entry = ManualResultEntry.objects.create(
                    user=request.user,
                    roll_number=f"manual-{request.user.id}-{ManualResultEntry.objects.filter(user=request.user).count()+1}",
                    name=request.user.get_full_name() or request.user.username,
                    marks_data={s['name']: {
                        'total': s['marks'],
                        'credit': s['credit'],
                        'max_marks': s['total_marks'],
                        'percent': s['percent'],
                        'grade_point': s['grade_point'],
                    } for s in subjects}
                )
                entry.total_marks = total_marks
                entry.percentage = (total_marks / max_total_marks) * 100 if max_total_marks else 0
                entry.save()

            # Log query for all
            from .models import ResultQuery
            ResultQuery.objects.create(
                roll_number=f"manual-{request.user.id if request.user.is_authenticated else 'anon'}",
                user=request.user if request.user.is_authenticated else None,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                result_found=True,
                semester="manual",
                branch="manual"
            )
        else:
            show_result = False
            error = "Please fill all required fields correctly."
    else:
        formset = ManualSubjectFormSet()

    context = {
        'formset': formset,
        'show_result': show_result,
        'subjects_data': subjects_data,
        'sgpa': sgpa,
        'total_marks': total_marks,
        'show_full': show_full,
        'error': error,
        'title': 'Manual SGPA Calculator',
        'meta_description': 'Manually calculate your SGPA by entering your own subjects and marks.',
        'allow_image_download': show_result,  # for template to show download option
    }
    return render(request, 'results/manual_calculator.html', context)
