from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from . import lockout
from .models import CustomUser


class EmailAuthenticationForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'No pudimos iniciar sesión con ese usuario/correo y PIN o contraseña.',
        'inactive': 'Esta cuenta está inactiva.',
        'locked': 'Esta cuenta quedó bloqueada por varios intentos fallidos. Espera 15 minutos o pide ayuda a tu docente.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Usuario o correo'
        self.fields['username'].widget.attrs.update({
            'class': 'login-page__input',
            'placeholder': 'usuario del estudiante o correo',
            'autocomplete': 'username',
        })
        self.fields['password'].label = 'PIN o contraseña'
        self.fields['password'].widget.attrs.update({
            'class': 'login-page__input',
            'placeholder': 'PIN del estudiante o contraseña',
            'autocomplete': 'current-password',
        })

    def clean(self):
        key = lockout.password_login_key(self.cleaned_data.get('username'))
        if lockout.is_locked(key):
            raise forms.ValidationError(self.error_messages['locked'], code='locked')
        try:
            cleaned_data = super().clean()
        except forms.ValidationError:
            lockout.register_failure(key)
            raise
        lockout.reset(key)
        return cleaned_data


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, label='Nombre')
    last_name = forms.CharField(max_length=150, label='Apellido')
    email = forms.EmailField(label='Correo electrónico')
    role = forms.ChoiceField(
        label='Tipo de cuenta',
        choices=(
            (CustomUser.Role.PARENT, 'Padre o tutor'),
        ),
    )
    grade = forms.ChoiceField(label='Grado', choices=(('1', 'Primer grado'), ('2', 'Segundo grado'), ('3', 'Tercer grado')), required=False)
    reading_level = forms.ChoiceField(label='Nivel de lectura', choices=(('1', 'Nivel 1'), ('2', 'Nivel 2'), ('3', 'Nivel 3')), required=False)

    password1 = forms.CharField(
        label='Contraseña',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='Tu contraseña debe tener al menos 8 caracteres.',
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='',
    )

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'username', 'email', 'role', 'grade', 'reading_level', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Nombre de usuario'
        self.fields['username'].help_text = ''

        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

        for field_name in ('role', 'grade', 'reading_level'):
            self.fields[field_name].widget.attrs['class'] = 'form-select'

        self.fields['email'].widget.attrs['autocomplete'] = 'email'
        self.fields['first_name'].widget.attrs['autocomplete'] = 'given-name'
        self.fields['last_name'].widget.attrs['autocomplete'] = 'family-name'

    def clean_role(self):
        role = self.cleaned_data['role']
        if role != CustomUser.Role.PARENT:
            raise forms.ValidationError('Solo padres o tutores pueden registrarse públicamente.')
        return role


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'gender', 'profile_photo')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].label = 'Nombres'
        self.fields['last_name'].label = 'Apellidos'
        self.fields['email'].label = 'Correo electrónico'
        self.fields['gender'].label = 'Sexo'
        self.fields['profile_photo'].label = 'Foto de perfil'
        self.fields['first_name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Ej. Administrador'})
        self.fields['last_name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Ej. Sistema'})
        self.fields['email'].widget.attrs.update({'class': 'form-control', 'placeholder': 'correo@ejemplo.com', 'autocomplete': 'email'})
        self.fields['gender'].widget.attrs.update({'class': 'form-select'})
        self.fields['profile_photo'].widget.attrs.update({'class': 'form-control', 'accept': 'image/*'})


class StudentProfileForm(forms.Form):
    grade = forms.ChoiceField(choices=(('1', 'Primer grado'), ('2', 'Segundo grado'), ('3', 'Tercer grado')))
    reading_level = forms.ChoiceField(choices=(('1', 'Nivel 1'), ('2', 'Nivel 2'), ('3', 'Nivel 3')))
