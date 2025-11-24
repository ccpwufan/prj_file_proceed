from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import PDFConversion, ConvertedImage

class PDFUploadForm(forms.ModelForm):
    processor = forms.ChoiceField(
        choices=[('', '-- Select a processor --'), ('ExpenseReport', 'ExpenseReport')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md'
        })
    )
    
    class Meta:
        model = PDFConversion
        fields = ['pdf_file', 'processor', 'comments']
        widgets = {
            'pdf_file': forms.FileInput(attrs={
                'accept': '.pdf',
                'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'
            }),
            'comments': forms.TextInput(attrs={
                'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
                'placeholder': 'Enter any notes about this conversion (optional)',
                'maxlength': 100
            })
        }
    
    def __init__(self, *args, **kwargs):
        super(PDFUploadForm, self).__init__(*args, **kwargs)
        self.fields['comments'].required = False
    
    def clean_pdf_file(self):
        pdf_file = self.cleaned_data.get('pdf_file')
        if pdf_file:
            if not pdf_file.name.lower().endswith('.pdf'):
                raise forms.ValidationError('Only PDF files are allowed.')
            if pdf_file.size > 50 * 1024 * 1024:  # 50MB limit
                raise forms.ValidationError('File size must be less than 50MB.')
        return pdf_file

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class ImageSelectionForm(forms.Form):
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get user's images, newest first
        if user.is_superuser:
            images = ConvertedImage.objects.all().order_by('-created_at')
        else:
            images = ConvertedImage.objects.filter(pdf_conversion__user=user).order_by('-created_at')
        
        self.fields['selected_images'] = forms.ModelMultipleChoiceField(
            queryset=images,
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'mr-2'}),
            required=True,
            label='Select images to analyze'
        )