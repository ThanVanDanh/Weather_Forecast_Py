# forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
# from .models_profile import UserProfile
from .models import UserProfile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(label="Địa chỉ Email", required=True)
    phone = forms.CharField(label="Số điện thoại", max_length=20, required=True)

    class Meta:
        model = User
        fields = ['last_name', 'first_name', 'username', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['username'].label = "Tên đăng nhập"

        if 'password1' in self.fields:
            self.fields['password1'].label = "Mật khẩu"
            self.fields['password1'].widget.attrs['placeholder'] = "Nhập mật khẩu"
        if 'password2' in self.fields:
            self.fields['password2'].label = "Xác nhận mật khẩu"
            self.fields['password2'].widget.attrs['placeholder'] = "Nhập lại mật khẩu"

        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
            if not field.widget.attrs.get('placeholder'):
                field.widget.attrs['placeholder'] = field.label

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone.isdigit():
            raise forms.ValidationError("Số điện thoại chỉ được chứa các ký tự số.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email này đã được đăng ký. Vui lòng sử dụng email khác.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']

        if commit:
            user.save()
            # Lưu số điện thoại vào bảng UserProfile
            phone = self.cleaned_data.get('phone')
            UserProfile.objects.get_or_create(user=user, defaults={'phone': phone})

        return user


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(label="Email", widget=forms.TextInput(
        attrs={'readonly': 'readonly'}))  # Email thường không cho sửa tùy tiện

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].label = "Tên"
        self.fields['last_name'].label = "Họ"
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone', 'address']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone'].label = "Số điện thoại"
        self.fields['address'].label = "Địa chỉ"
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'