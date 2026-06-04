from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from django.views.generic import CreateView
from django.urls import reverse_lazy


class UserLoginView(LoginView):
    template_name = "users/login.html"
    redirect_authenticated_user = True

    def form_invalid(self, form):
        messages.error(self.request, "Invalid username or password.")
        return super().form_invalid(form)


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("login")


class UserRegisterView(CreateView):
    form_class    = UserCreationForm
    template_name = "users/register.html"
    success_url   = reverse_lazy("index")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Account created successfully.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect("index")
        return super().dispatch(request, *args, **kwargs)