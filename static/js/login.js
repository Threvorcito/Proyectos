document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[data-login-password-toggle]').forEach(function (button) {
    button.addEventListener('click', function () {
      var input = document.getElementById(button.getAttribute('data-login-password-toggle'));
      if (!input) return;
      var showPassword = input.type === 'password';
      input.type = showPassword ? 'text' : 'password';
      button.setAttribute('aria-pressed', showPassword ? 'true' : 'false');
      button.setAttribute('aria-label', showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña');
    });
  });
});
