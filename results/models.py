from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ResultQuery(models.Model):
    """Model to track all result queries made on the website"""
    
    roll_number = models.CharField(max_length=20, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    result_found = models.BooleanField(default=False)
    semester = models.CharField(max_length=10, default='6th')
    branch = models.CharField(max_length=10, default='CSE')
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Result Query'
        verbose_name_plural = 'Result Queries'
    
    def __str__(self):
        return f"{self.roll_number} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class StudentResult(models.Model):
    """Model to store student results"""
    
    # Updated subject list with BT-609 as first subject (0 credit)
    SUBJECTS_DATA = {
        "semester": "6th",
        "branch": "CSE", 
        "college": "SCRIET",
        "subjects": [
            {
                "code": "BT-609",
                "name": "Non-Credit Subject",
                "credit": 0
            },
            {
                "code": "BT-612", 
                "name": "Software Engineering",
                "credit": 4
            },
            {
                "code": "BT-613",
                "name": "Computer Networks", 
                "credit": 4
            },
            {
                "code": "BT-614",
                "name": "Compiler Design",
                "credit": 4
            },
            {
                "code": "BT-615",
                "name": "Software Project Management",
                "credit": 3
            },
            {
                "code": "BT-616",
                "name": "Big Data",
                "credit": 3
            },
            {
                "code": "BT-662",
                "name": "Software Engineering Lab",
                "credit": 1
            },
            {
                "code": "BT-663", 
                "name": "Computer Networks Lab",
                "credit": 1
            },
            {
                "code": "BT-664",
                "name": "Compiler Design Lab", 
                "credit": 1
            }
        ]
    }
    
    roll_number = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100)
    
    # Subject marks - storing as JSON field for flexibility
    marks_data = models.JSONField(help_text="Stores theory, internal, and viva marks for all subjects")
    
    # Calculated fields
    total_marks = models.IntegerField(null=True, blank=True)
    percentage = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['roll_number']
        verbose_name = 'Student Result'
        verbose_name_plural = 'Student Results'
    
    def __str__(self):
        return f"{self.roll_number} - {self.name}"
    
    @classmethod
    def get_subject_by_index(cls, index):
        """Get subject info by index"""
        try:
            return cls.SUBJECTS_DATA['subjects'][index]
        except IndexError:
            return None
    
    def parse_marks_from_raw_data(self, raw_marks_list):
        """
        Parse marks from the raw data format:
        [['Marks obtained (In Theory)', '', '', '', '', '', '', '', '', '57', '47', '52', '31', '51', '56', '44', '39', '42', ...],
         ['Marks Obtained (In Internal/ Practical)', '', '', '', '', '', '', '', '', '22', '28', '17', '26', '27', '27', '45', '41', '43', ...],
         ['Marks Obtained (Viva Voce)', '', '', '', '', '', '', '', '', '+++', '+', '+', '', '', '', '', '', '', ...]]
        """
        if not raw_marks_list or len(raw_marks_list) < 2:
            return {}
        
        theory_marks = raw_marks_list[0][9:18]  # Extract marks for 9 subjects
        internal_marks = raw_marks_list[1][9:18]  # Extract marks for 9 subjects
        viva_marks = raw_marks_list[2][9:18] if len(raw_marks_list) > 2 else [''] * 9
        
        parsed_data = {}
        subjects = self.SUBJECTS_DATA['subjects']
        
        for i, subject in enumerate(subjects):
            subject_code = subject['code']
            credit = subject['credit']
            
            # Parse theory marks (convert empty strings to 0)
            theory = 0
            if i < len(theory_marks) and theory_marks[i] and theory_marks[i].strip():
                try:
                    theory = int(theory_marks[i].strip())
                except ValueError:
                    theory = 0
            
            # Parse internal marks
            internal = 0
            if i < len(internal_marks) and internal_marks[i] and internal_marks[i].strip():
                try:
                    internal = int(internal_marks[i].strip())
                except ValueError:
                    internal = 0
            
            # Parse viva marks (usually +++ or + for pass)
            viva = viva_marks[i] if i < len(viva_marks) else ''
            
            # Calculate total for subject
            if credit == 0:  # Non-credit subject
                total = theory + internal
            elif credit == 1:  # Lab subjects (50-50 distribution)
                total = theory + internal
            else:  # Theory subjects (30-70 distribution)
                total = theory + internal
            
            parsed_data[subject_code] = {
                'theory': theory,
                'internal': internal,
                'viva': viva,
                'total': total,
                'credit': credit
            }
        
        return parsed_data
    
    def calculate_totals(self):
        """Calculate total marks and percentage"""
        if not self.marks_data:
            return
        
        total_marks = 0
        total_credits = 0
        
        for subject_code, marks in self.marks_data.items():
            total_marks += marks.get('total', 0)
            total_credits += marks.get('credit', 0)
        
        self.total_marks = total_marks
        if total_credits > 0:
            # Calculate percentage based on total possible marks
            # Assuming max marks per credit is 100 for simplicity
            max_possible = sum([
                100 if s['credit'] > 0 else 100 
                for s in self.SUBJECTS_DATA['subjects']
            ])
            self.percentage = (total_marks / max_possible) * 100 if max_possible > 0 else 0
    
    def save(self, *args, **kwargs):
        self.calculate_totals()
        super().save(*args, **kwargs)


class ManualResultEntry(models.Model):
    """Model for users to manually enter their marks"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    roll_number = models.CharField(max_length=20, db_index=True)
    name = models.CharField(max_length=100, blank=True)
    
    # Store marks as JSON for flexibility
    marks_data = models.JSONField(help_text="Manually entered marks data")
    
    # Calculated fields
    total_marks = models.IntegerField(null=True, blank=True)
    percentage = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Manual Result Entry'
        verbose_name_plural = 'Manual Result Entries'
    
    def __str__(self):
        return f"{self.roll_number} - Manual Entry"
    
    def calculate_totals(self):
        """Calculate total marks and percentage from manual entry"""
        if not self.marks_data:
            return
        
        total_marks = 0
        for subject_code, marks in self.marks_data.items():
            total_marks += marks.get('total', 0)
        
        self.total_marks = total_marks
        # Calculate percentage (assuming 900 max marks for 9 subjects)
        max_possible = 900  # Rough estimate
        self.percentage = (total_marks / max_possible) * 100 if max_possible > 0 else 0
    
    def save(self, *args, **kwargs):
        self.calculate_totals()
        super().save(*args, **kwargs)
