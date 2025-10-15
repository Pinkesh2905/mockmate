from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from .models import (
    PracticeProblem, TestCase, Category, Tag,
    Discussion, DIFFICULTY_CHOICES, PROGRAMMING_LANGUAGES,
    ProblemVideoSolution, Badge
)
import json
import csv
import io

class ProblemFilterForm(forms.Form):
    """Form for filtering problems in the problem list"""
    difficulty = forms.ChoiceField(
        choices=[('', 'All Difficulties')] + list(DIFFICULTY_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select rounded-lg border-gray-300'})
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select rounded-lg border-gray-300'})
    )
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-checkbox'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input rounded-lg border-gray-300',
            'placeholder': 'Search problems...'
        })
    )
    company = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input rounded-lg border-gray-300',
            'placeholder': 'Company name...'
        })
    )
    status = forms.ChoiceField(
        choices=[
            ('', 'All Problems'),
            ('solved', 'Solved'),
            ('attempted', 'Attempted'),
            ('not_attempted', 'Not Attempted')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select rounded-lg border-gray-300'})
    )

class ProblemForm(forms.ModelForm):
    """Enhanced form for creating/editing problems"""
    
    class Meta:
        model = PracticeProblem
        fields = [
            'title', 'difficulty', 'category', 'tags', 'companies',
            'statement', 'constraints', 'hints', 'approach',
            'time_complexity', 'space_complexity', 'time_limit', 'memory_limit',
            'leetcode_url', 'hackerrank_url', 'external_url', 'is_premium', 'is_private'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter problem title'
            }),
            'difficulty': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'tags': forms.CheckboxSelectMultiple(attrs={
                'class': 'grid grid-cols-2 md:grid-cols-3 gap-2'
            }),
            'companies': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Comma-separated companies (e.g., Google, Amazon, Microsoft)'
            }),
            'statement': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 12,
                'placeholder': 'Enter detailed problem description with examples'
            }),
            'constraints': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 4,
                'placeholder': 'Enter problem constraints (e.g., 1 ≤ n ≤ 10^5)'
            }),
            'hints': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 4,
                'placeholder': 'Enter hints as JSON array: ["Hint 1", "Hint 2"]'
            }),
            'approach': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 6,
                'placeholder': 'Describe the approach to solve this problem'
            }),
            'time_complexity': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'e.g., O(n log n)'
            }),
            'space_complexity': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'e.g., O(n)'
            }),
            'time_limit': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'min': '1',
                'max': '10'
            }),
            'memory_limit': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'min': '32',
                'max': '512'
            }),
            'leetcode_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'https://leetcode.com/problems/...'
            }),
            'hackerrank_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'https://hackerrank.com/challenges/...'
            }),
            'external_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Any other external URL'
            }),
            'is_premium': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'
            }),
            'is_private': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'
            }),
        }
        
        labels = {
            'time_complexity': 'Time Complexity',
            'space_complexity': 'Space Complexity',
            'time_limit': 'Time Limit (seconds)',
            'memory_limit': 'Memory Limit (MB)',
            'leetcode_url': 'LeetCode URL',
            'hackerrank_url': 'HackerRank URL',
            'external_url': 'External URL',
            'is_premium': 'Premium Problem',
            'is_private': 'Private Problem (only visible to owner)',
        }

    def clean_hints(self):
        hints = self.cleaned_data.get('hints')
        if hints:
            try:
                if isinstance(hints, str):
                    parsed_hints = json.loads(hints)
                else:
                    parsed_hints = hints
                    
                if not isinstance(parsed_hints, list):
                    raise ValidationError("Hints must be a JSON array of strings.")
                return parsed_hints
            except json.JSONDecodeError:
                return [hints] if hints else []
        return []

    def clean_companies(self):
        companies = self.cleaned_data.get('companies', '')
        if companies:
            # Clean and normalize company names
            company_list = [company.strip() for company in companies.split(',') if company.strip()]
            return ', '.join(company_list)
        return ''

class TestCaseUploadForm(forms.Form):
    """Form for uploading test cases via CSV"""
    csv_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'accept': '.csv'
        }),
        help_text="Upload CSV file with columns: input_data, expected_output, is_sample, is_hidden, description, difficulty_weight, order"
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        
        if not csv_file.name.endswith('.csv'):
            raise ValidationError("File must be a CSV file.")
        
        if csv_file.size > 5 * 1024 * 1024:  # 5MB limit
            raise ValidationError("File size must be less than 5MB.")
        
        # Validate CSV structure
        try:
            csv_file.seek(0)
            content = csv_file.read().decode('utf-8')
            csv_file.seek(0)
            
            reader = csv.DictReader(io.StringIO(content))
            required_fields = ['input_data', 'expected_output']
            
            if not all(field in reader.fieldnames for field in required_fields):
                raise ValidationError(f"CSV must contain columns: {', '.join(required_fields)}")
            
            # Validate first few rows
            row_count = 0
            for row in reader:
                if row_count >= 3:  # Check first 3 rows
                    break
                if not row['input_data'] or not row['expected_output']:
                    raise ValidationError("Input data and expected output cannot be empty.")
                row_count += 1
                
        except Exception as e:
            raise ValidationError(f"Invalid CSV file: {str(e)}")
        
        return csv_file

class TestCaseForm(forms.ModelForm):
    """Form for individual test cases"""
    
    class Meta:
        model = TestCase
        fields = [
            'input_data', 'expected_output', 'is_sample', 'is_hidden',
            'description', 'explanation', 'difficulty_weight', 'order'
        ]
        widgets = {
            'input_data': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono',
                'rows': 4,
                'placeholder': 'Enter input data'
            }),
            'expected_output': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono',
                'rows': 4,
                'placeholder': 'Enter expected output'
            }),
            'description': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Brief description of this test case'
            }),
            'explanation': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 3,
                'placeholder': 'Explanation of this test case (for sample cases)'
            }),
            'difficulty_weight': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'min': '1',
                'max': '10'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'min': '0'
            }),
            'is_sample': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'
            }),
            'is_hidden': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'
            })
        }

# Formsets for inline editing
TestCaseFormSet = inlineformset_factory(
    PracticeProblem,
    TestCase,
    form=TestCaseForm,
    extra=2,
    can_delete=True,
    min_num=1,
    validate_min=True
)

class DiscussionForm(forms.ModelForm):
    """Form for creating discussions"""
    
    class Meta:
        model = Discussion
        fields = ['title', 'content', 'is_solution']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter discussion title'
            }),
            'content': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 8,
                'placeholder': 'Share your thoughts, solution, or ask questions...'
            }),
            'is_solution': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'
            })
        }
        
        labels = {
            'is_solution': 'This is a solution discussion'
        }

class CodeSubmissionForm(forms.Form):
    """Form for code submission"""
    language = forms.ChoiceField(
        choices=PROGRAMMING_LANGUAGES,
        widget=forms.Select(attrs={
            'class': 'px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'onchange': 'changeLanguage(this.value)'
        })
    )
    code = forms.CharField(
        widget=forms.Textarea(attrs={
            'id': 'code-editor',
            'class': 'hidden'  # Hidden because we'll use Monaco editor
        })
    )
    
class CustomTestForm(forms.Form):
    """Form for running custom test cases"""
    language = forms.ChoiceField(choices=PROGRAMMING_LANGUAGES)
    code = forms.CharField(widget=forms.Textarea)
    input_data = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Enter your test input here...',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono'
        }),
        required=False
    )

class CategoryForm(forms.ModelForm):
    """Form for creating/editing categories"""
    
    class Meta:
        model = Category
        fields = ['name', 'description', 'color_code']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Category name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 4,
                'placeholder': 'Category description'
            }),
            'color_code': forms.TextInput(attrs={
                'type': 'color',
                'class': 'w-20 h-10 border border-gray-300 rounded-lg'
            })
        }

class TagForm(forms.ModelForm):
    """Form for creating/editing tags"""
    
    class Meta:
        model = Tag
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Tag name'
            })
        }

class ProblemVideoSolutionForm(forms.ModelForm):
    """Form for adding a video solution to a problem"""
    
    class Meta:
        model = ProblemVideoSolution
        fields = ['title', 'url', 'is_premium']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Video title (e.g., "Python Solution Explained")'
            }),
            'url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'https://www.youtube.com/watch?v=...'
            }),
            'is_premium': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'
            })
        }

class BadgeForm(forms.ModelForm):
    """Form for creating/editing badges"""
    
    class Meta:
        model = Badge
        fields = ['name', 'description', 'image_url']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Badge name (e.g., "First Accepted Submission")'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 4,
                'placeholder': 'Description of the achievement'
            }),
            'image_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'URL to an image for the badge'
            }),
        }

class BulkProblemUploadForm(forms.Form):
    """Form for bulk uploading problems from CSV"""
    csv_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'accept': '.csv'
        }),
        help_text="Upload CSV file with problem data"
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        
        if not csv_file.name.endswith('.csv'):
            raise ValidationError("File must be a CSV file.")
        
        if csv_file.size > 10 * 1024 * 1024:  # 10MB limit
            raise ValidationError("File size must be less than 10MB.")
        
        return csv_file
    
# Add this import at the top with other model imports
from .models import (
    PracticeProblem, TestCase, Category, Tag, CodeTemplate,  # Add CodeTemplate here
    Discussion, DIFFICULTY_CHOICES, PROGRAMMING_LANGUAGES,
    ProblemVideoSolution, Badge
)

class CodeTemplateForm(forms.ModelForm):
    """Form for individual code templates"""
    
    class Meta:
        model = CodeTemplate
        fields = ['language', 'starter_code', 'solution_code', 'is_default']
        widgets = {
            'language': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'starter_code': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono',
                'rows': 10,
                'placeholder': 'Enter starter code template...'
            }),
            'solution_code': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono',
                'rows': 10,
                'placeholder': 'Enter solution code (optional)...'
            }),
            'is_default': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'
            })
        }

# Add this formset after TestCaseFormSet
CodeTemplateFormSet = inlineformset_factory(
    PracticeProblem,
    CodeTemplate,
    form=CodeTemplateForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)