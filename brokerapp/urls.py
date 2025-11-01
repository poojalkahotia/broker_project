from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import path, reverse_lazy
from . import views_org
urlpatterns = [
    
    # Party URLs
    path('parties/', views.party_view, name='party'),
    path('parties/edit/<str:pk>/', views.party_view, name='party_edit'),
    path('parties/delete/<str:pk>/', views.party_delete, name='party_delete'),
    
    path('broker/', views.broker_view, name='broker'),
    path('broker/edit/<str:pk>/', views.broker_view, name='broker_edit'),
    path('broker/delete/<str:pk>/', views.broker_delete, name='broker_delete'),
    
    path('items/', views.item_view, name='item'),
    
    # Authentication URLs
    path("login/", auth_views.LoginView.as_view(template_name="auth/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("password_change/",login_required (auth_views.PasswordChangeView.as_view(template_name="auth/password_change.html", success_url=reverse_lazy('password_change_done'))), name="password_change"),
    path("password_change/done/",login_required (auth_views.PasswordChangeDoneView.as_view(template_name="auth/password_change_done.html")), name="password_change_done"),

    # Root URL redirects to login page
    path("", auth_views.LoginView.as_view(template_name="auth/login.html")),

    # Dashboard
    path("dashboard/", views.dashboard, name='dashboard'),

    path('sale/', views.sale_form, name='sale_form_new'),
    path('sale/<int:invno>/', views.sale_form, name='sale_form_update'),
    path('sale/save/', views.save_sale, name='save_sale'),
    path('sale/update/<int:invno>/', views.update_sale, name='update_sale'),
    path('sale/delete/<int:invno>/', views.delete_sale, name='delete_sale'),
    path('saledata/', views.sale_data_view, name='saledata'),
    
    path("sale-report/", views.sale_report, name="sale_report"),
    path("bardana-report/", views.bardana_report, name="bardana_report"),
    
    # --- PURCHASE URLs ---
    path('purchase/', views.purchase_form, name='purchase_form_new'),
    path('purchase/<int:invno>/', views.purchase_form, name='purchase_form_update'),
    path('purchase/save/', views.save_purchase, name='save_purchase'),
    path('purchase/update/<int:invno>/', views.update_purchase, name='update_purchase'),
    path('purchase/delete/<int:invno>/', views.delete_purchase, name='delete_purchase'),
    path('purchasedata/', views.purchase_data_view, name='purchasedata'),
    path("purchase-report/", views.purchase_report, name="purchase_report"),
    
    path('daily-page/', views.daily_page_view, name='daily_page'),
    path('daily-page/show/', views.daily_page_show, name='daily_page_show'),         # GET entries for a date (AJAX)
    path('daily-page/jama/add/', views.daily_page_jama_add, name='daily_page_jama_add'),   # POST
    path('daily-page/naame/add/', views.daily_page_naame_add, name='daily_page_naame_add'),# POST
    path('daily-page/jama/delete/<int:entry_no>/', views.daily_page_jama_delete, name='daily_page_jama_delete'),
    path('daily-page/naame/delete/<int:entry_no>/', views.daily_page_naame_delete, name='daily_page_naame_delete'),
    path('daily-page/pdf/', views.daily_page_pdf, name='daily_page_pdf'),
    
    #org
    path("org/new/", views_org.org_create, name="org_create"),
    path("org/switch/", views_org.org_switch, name="org_switch"),
    path("org/edit/", views_org.org_edit, name="org_edit"),
    path("employees/add/", views_org.employee_add, name="employee_add"),
    path("employees/", views_org.employee_list, name="employee_list"),
    path("employees/<int:user_id>/edit/", views_org.employee_edit, name="employee_edit"),
    path("employees/<int:user_id>/remove/", views_org.employee_remove, name="employee_remove"),

]



