from django.db.models import Count
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseNotFound, HttpResponseServerError


from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect, reverse

from django.views.generic import ListView, TemplateView, View, CreateView, DetailView, UpdateView

from vacancies.forms import ApplicationForm, CompanyForm, VacancyForm
from vacancies.models import Company, Specialty, Vacancy


class MainView(TemplateView):
    template_name = "public/index.html"

    def get_context_data(self, **kwargs):
        context = super(MainView, self).get_context_data(**kwargs)
        context["speciality_list"] = Specialty.objects.annotate(vacancy_count=Count("vacancies"))
        context["company_list"] = Company.objects.annotate(vacancy_count=Count("vacancies"))
        return context


class VacanciesListView(ListView):
    model = Vacancy
    template_name = "public/vacancies.html"

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(VacanciesListView, self).get_context_data(**kwargs)
        count_vacan = Vacancy.objects.aggregate(vacancy_count=Count("id"))
        context["count_vacancy"] = count_vacan["vacancy_count"]
        return context


class VacanciesBySpecialityView(ListView):
    template_name = "public/vacancies.html"

    def get_queryset(self):
        self.speciality = get_object_or_404(Specialty, code=self.kwargs["code"])
        self.queryset = self.speciality.vacancies.all()
        return super(VacanciesBySpecialityView, self).get_queryset()

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context["speciality_title"] = self.speciality.title
        context["speciality_id"] = self.speciality.id
        spec_count = Specialty.objects.annotate(vacancy_count=Count("vacancies"))
        for count in spec_count:
            if self.speciality.id == count.id:
                context["count_vacancy"] = count.vacancy_count
        return context


class VacanciesByCompanyView(ListView):
    template_name = "public/company.html"

    def get_queryset(self):
        self.company = get_object_or_404(Company, pk=self.kwargs["id"])
        self.queryset = self.company.vacancies.all()
        return super(VacanciesByCompanyView, self).get_queryset()

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context["company_name"] = self.company.name
        context["company_location"] = self.company.location
        context["company_id"] = self.company.id
        context["count_in_company"] = Company.objects.annotate(vacancy_count=Count("vacancies"))
        context["company_logo"] = self.company.logo
        return context


class DetailVacancyView(DetailView):
    model = Vacancy
    template_name = "vacancies/vacancy.html"
    form_class = ApplicationForm

    def get_context_data(self, form=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = form or self.form_class()
        return context

    def post(self, request, pk):
        form = self.form_class(request.POST)
        if form.is_valid():
            aplication = form.save(commit=False)
            aplication.user = request.user
            aplication.vacancy_id = pk
            aplication.save()
            return redirect("send", pk)
        self.object = self.get_object()
        return self.render_to_response(self.get_context_data(form=form))


class SendVacancyView(View):
    template_name = "vacancies/send.html"

    def get(self, request, pk):
        return render(request, "vacancies/send.html")


class MyCompanyEditView(View):
    template_name = "vacancies/company-create.html"

    def get(self, request):
        return render(request, "company/company-create.html")


class MyCompanyCreateView(CreateView):
    model = Company
    form_class = CompanyForm

    def dispatch(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            company.owner_id = request.user.pk
            company.save()
            return redirect("my_company")
        else:
            form = CompanyForm()
            return render(request, "company/company-edit.html", context={"form": form})


class MyCompanyView(UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = "company/company-edit.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            if Company.objects.filter(owner=request.user).exists():
                company = request.user.company
                form = self.form_class(request.POST, request.FILES, instance=Company.objects.get(owner=request.user.pk))
                if form.is_valid():
                    company = form.save()
                    return redirect(reverse("my_company"))
                return render(request, template_name=self.template_name, context={"form": form, "company": company})
            else:
                return redirect("company_edit")
        except ObjectDoesNotExist:
            return HttpResponseNotFound


class Vacancy_listCompanyView(ListView):
    model = Company
    template_name = "company/vacancy-list.html"

    def get(self, request, *args, **kwargs):
        try:
            Company.objects.get(owner_id=request.user.id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound
        return super().get(request, *args, **kwargs)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context["vacancy_list"] = Vacancy.objects.filter(company__owner=self.request.user.id)
        return context


class MyVacancyCreateView(CreateView):
    model = Vacancy
    form_class = VacancyForm
    template_name = "company/vacancy-edit.html"

    def dispatch(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            vacancy = form.save(commit=False)
            vacancy.company_id = request.user.company.pk
            vacancy.save()
            return redirect("company_vacancies")
        else:
            form = CompanyForm()
            return render(request, "company/vacancy-edit.html", context={"form": form})


class OneVacancyByCompanyView(UpdateView, ListView):
    model = Vacancy
    form_class = VacancyForm
    template_name = "vacancies/vacancy-edit.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            vacancy = Vacancy.objects.filter(company__owner=self.request.user).get(id=self.kwargs["vacancy_id"])
            form = self.form_class(request.POST, request.FILES, instance=vacancy)
            if form.is_valid():
                form.save()
                return redirect(reverse("company_vacancies"))
            return render(request, "vacancies/vacancy-edit.html", context={"form": form, "vacancy": vacancy})
        except ObjectDoesNotExist:
            return HttpResponseNotFound


class CustomHendler():
    def custom_handler404(request, exception):
        return HttpResponseNotFound('Ресурс не найден!')

    def custom_handler500(request):
        return HttpResponseServerError('Ошибка сервера!')
