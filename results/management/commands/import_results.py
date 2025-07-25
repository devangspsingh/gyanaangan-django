import pandas as pd
import json
import ast
from django.core.management.base import BaseCommand
from results.models import StudentResult

def get_8th_sem_subjects_v2():
    return [
        {"code": "BT-801", "name": "Rural Development: Administration and Planning", "credit": 3, "max_marks": 150},
        {"code": "BT-816", "name": "Cloud Computing", "credit": 3, "max_marks": 150},
        {"code": "BT-817", "name": "Data Warehousing & Data Mining", "credit": 3, "max_marks": 150},
        {"code": "BT-866", "name": "Project", "credit": 9, "max_marks": 400}
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

class Command(BaseCommand):
    help = 'Import student results from Excel file'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Path to the Excel file')
        parser.add_argument('--sheet', type=str, default=0, help='Sheet name or index')

    def handle(self, *args, **options):
        excel_file = options['excel_file']
        sheet = options['sheet']
        
        try:
            # Read Excel file
            df = pd.read_excel(excel_file, sheet_name=sheet)
            
            # Subject mapping based on roll number ranges
            def get_subjects_for_roll_number(roll_number):
                """Return subject list based on roll number range"""
                try:
                    roll_int = int(roll_number)
                    # 8th sem IT (100210500-100210600)
                    if 100210500 <= roll_int <= 100210600:
                        return get_8th_sem_subjects_v2(), "IT-8TH"
                    # IT Branch (100220500-600) - Different subjects
                    elif 100220500 <= roll_int <= 100220600:
                        return [
                            {"code": "BT-609", "name": "Essence of Indian Traditional Knowledge", "credit": 0, "max_marks": 100},
                            {"code": "BT-612", "name": "Software Engineering", "credit": 4, "max_marks": 100},
                            {"code": "BT-613", "name": "Computer Networks", "credit": 4, "max_marks": 100},
                            {"code": "BT-617", "name": "Data Analytics", "credit": 4, "max_marks": 100},
                            {"code": "BT-615", "name": "Software Project Management", "credit": 3, "max_marks": 100},
                            {"code": "BT-618", "name": "Augmented & Virtual Reality", "credit": 3, "max_marks": 100},
                            {"code": "BT-662", "name": "Software Engineering Lab", "credit": 1, "max_marks": 100},
                            {"code": "BT-663", "name": "Computer Networks Lab", "credit": 1, "max_marks": 100},
                            {"code": "BT-667", "name": "Data Analytics Lab", "credit": 1, "max_marks": 100}
                        ], "IT"
                    # CSE Branch (100220101 onwards) - Original subjects  
                    else:
                        return [
                            {"code": "BT-609", "name": "Essence of Indian Traditional Knowledge", "credit": 0, "max_marks": 100},
                            {"code": "BT-612", "name": "Software Engineering", "credit": 4, "max_marks": 100},
                            {"code": "BT-613", "name": "Computer Networks", "credit": 4, "max_marks": 100},
                            {"code": "BT-614", "name": "Compiler Design", "credit": 4, "max_marks": 100},
                            {"code": "BT-615", "name": "Software Project Management", "credit": 3, "max_marks": 100},
                            {"code": "BT-616", "name": "Big Data", "credit": 3, "max_marks": 100},
                            {"code": "BT-662", "name": "Software Engineering Lab", "credit": 1, "max_marks": 100},
                            {"code": "BT-663", "name": "Computer Networks Lab", "credit": 1, "max_marks": 100},
                            {"code": "BT-664", "name": "Compiler Design Lab", "credit": 1, "max_marks": 100}
                        ], "CSE"
                except ValueError:
                    # Default to CSE if roll number parsing fails
                    return [
                        {"code": "BT-609", "name": "Essence of Indian Traditional Knowledge", "credit": 0, "max_marks": 100},
                        {"code": "BT-612", "name": "Software Engineering", "credit": 4, "max_marks": 100},
                        {"code": "BT-613", "name": "Computer Networks", "credit": 4, "max_marks": 100},
                        {"code": "BT-614", "name": "Compiler Design", "credit": 4, "max_marks": 100},
                        {"code": "BT-615", "name": "Software Project Management", "credit": 3, "max_marks": 100},
                        {"code": "BT-616", "name": "Big Data", "credit": 3, "max_marks": 100},
                        {"code": "BT-662", "name": "Software Engineering Lab", "credit": 1, "max_marks": 100},
                        {"code": "BT-663", "name": "Computer Networks Lab", "credit": 1, "max_marks": 100},
                        {"code": "BT-664", "name": "Compiler Design Lab", "credit": 1, "max_marks": 100}
                    ], "CSE"
            
            imported_count = 0
            skipped_count = 0
            
            for index, row in df.iterrows():
                try:
                    # Extract basic info - handle both Excel columns and raw data
                    if len(row) >= 5:
                        # Excel format: col0=roll, col1=empty, col2=name, col3=father, col4=marks
                        roll_number = str(row.iloc[0]).strip()
                        student_name = str(row.iloc[2]).strip()
                        father_name = str(row.iloc[3]).strip()
                        marks_data = row.iloc[4]
                    else:
                        # Raw data format: might be different structure
                        roll_number = str(row.iloc[0]).strip()
                        student_name = str(row.iloc[1]).strip() if len(row) > 1 else ""
                        father_name = str(row.iloc[2]).strip() if len(row) > 2 else ""
                        marks_data = row.iloc[3] if len(row) > 3 else row.iloc[-1]
                    
                    # Clean roll number (remove scientific notation if present)
                    if 'E+' in roll_number or 'e+' in roll_number:
                        try:
                            roll_number = str(int(float(roll_number)))
                        except:
                            pass
                    
                    # Get subjects for this roll number
                    subjects, branch = get_subjects_for_roll_number(roll_number)
                    
                    # Skip if roll number already exists
                    if StudentResult.objects.filter(roll_number=roll_number).exists():
                        self.stdout.write(f"Skipping {roll_number} - already exists")
                        skipped_count += 1
                        continue
                    
                    # Parse marks data
                    marks_array = None
                    if isinstance(marks_data, str):
                        try:
                            marks_array = ast.literal_eval(marks_data)
                        except Exception as e:
                            self.stdout.write(f"Error parsing marks for {roll_number}: {str(e)}")
                            continue
                    elif isinstance(marks_data, list):
                        marks_array = marks_data
                    else:
                        self.stdout.write(f"Invalid marks data format for {roll_number}")
                        continue
                    
                    # Extract marks for each subject
                    theory_marks = []
                    internal_marks = []
                    viva_marks = []
                    
                    if marks_array and len(marks_array) > 0:
                        # Get theory marks (first array)
                        if len(marks_array[0]) > 1:
                            theory_marks = marks_array[0][1:]  # Skip the label
                        elif len(marks_array[0]) == 1:
                            theory_marks = marks_array[0]
                        
                        # Get internal marks (second array)
                        if len(marks_array) > 1 and len(marks_array[1]) > 1:
                            internal_marks = marks_array[1][1:]  # Skip the label
                        elif len(marks_array) > 1 and len(marks_array[1]) == 1:
                            internal_marks = marks_array[1]
                        
                        # Get viva marks (third array) - optional
                        if len(marks_array) > 2 and len(marks_array[2]) > 1:
                            viva_marks = marks_array[2][1:]  # Skip the label
                    
                    # Process marks for each subject
                    subject_marks = {}
                    for i, subject in enumerate(subjects):
                        subject_code = subject['code']
                        max_marks = subject.get('max_marks', 100)
                        
                        # Find the actual data starting index (skip empty strings at beginning)
                        data_start_index = 0
                        for idx, val in enumerate(theory_marks):
                            if val and val != '':
                                data_start_index = idx
                                break
                        marks_idx = data_start_index + i
                        theory = None
                        internal = None
                        # Extract theory marks
                        if marks_idx < len(theory_marks):
                            theory_val = theory_marks[marks_idx]
                            if theory_val and str(theory_val).strip() != '' and str(theory_val) != 'nan':
                                try:
                                    theory = int(float(str(theory_val)))
                                except (ValueError, TypeError):
                                    theory = None
                        # Extract internal marks
                        if marks_idx < len(internal_marks):
                            internal_val = internal_marks[marks_idx]
                            if internal_val and str(internal_val).strip() != '' and str(internal_val) != 'nan':
                                try:
                                    internal = int(float(str(internal_val)))
                                except (ValueError, TypeError):
                                    internal = None
                        total = (theory or 0) + (internal or 0)
                        subject_marks[subject_code] = {
                            'theory': theory,
                            'internal': internal,
                            'viva': '',  # Add viva field
                            'total': total,
                            'credit': subject['credit'],
                            'name': subject['name'],
                            'max_marks': max_marks
                        }
                    
                    # Calculate CGPA
                    total_points = 0
                    total_credits = 0
                    for subject_code, marks in subject_marks.items():
                        credit = marks['credit']
                        if credit > 0 and marks['theory'] is not None and marks['internal'] is not None:
                            total_marks = marks['theory'] + marks['internal']
                            max_marks = marks.get('max_marks', 100)
                            # 8th sem IT: grade point by percentage
                            if branch == "IT-8TH":
                                percent = (total_marks / max_marks) * 100 if max_marks else 0
                                grade_point = get_grade_point_by_percentage(percent)
                            else:
                                # Grade point calculation (10-point scale)
                                if total_marks >= 90:
                                    grade_point = 10
                                elif total_marks >= 80:
                                    grade_point = 9
                                elif total_marks >= 70:
                                    grade_point = 8
                                elif total_marks >= 60:
                                    grade_point = 7
                                elif total_marks >= 50:
                                    grade_point = 6
                                elif total_marks >= 40:
                                    grade_point = 5
                                else:
                                    grade_point = 0
                            total_points += grade_point * credit
                            total_credits += credit
                    cgpa = round(total_points / total_credits, 2) if total_credits > 0 else 0
                    
                    # Create StudentResult object
                    student_result = StudentResult.objects.create(
                        roll_number=roll_number,
                        name=student_name,
                        father_name=father_name,
                        marks_data=subject_marks
                    )
                    
                    imported_count += 1
                    self.stdout.write(f"Imported {roll_number} - {student_name} ({branch} Branch, CGPA: {cgpa})")
                    
                except Exception as e:
                    self.stdout.write(f"Error processing row {index} (Roll: {roll_number if 'roll_number' in locals() else 'unknown'}): {str(e)}")
                    # Debug info
                    if 'marks_array' in locals():
                        self.stdout.write(f"  Marks array structure: {len(marks_array) if marks_array else 'None'} arrays")
                        if marks_array:
                            for j, arr in enumerate(marks_array):
                                self.stdout.write(f"    Array {j}: length {len(arr) if arr else 0}")
                    continue
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully imported {imported_count} records. Skipped {skipped_count} existing records.'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error reading Excel file: {str(e)}')
            )
