"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from users.views import BrigaLoginView, accept_invite, account, android_asset_links, apple_app_site_association, control_center, dashboard, register, senior_easy, service_worker, health, protected_media, privacy_policy, push_subscribe, sophie_speech, terms

urlpatterns = [
    path('.well-known/assetlinks.json', android_asset_links, name='android_app_links'),
    path('.well-known/apple-app-site-association', apple_app_site_association, name='apple_universal_links'),
    path('admin/', admin.site.urls),
    path('', dashboard, name='pocetna'),
    path('jednostavno/', senior_easy, name='jednostavno'),
    path('prijava/', BrigaLoginView.as_view(), name='prijava'),
    path('odjava/', auth_views.LogoutView.as_view(), name='odjava'),
    path('registracija/', register, name='registracija'),
    path('poziv/<uuid:token>/', accept_invite, name='poziv'),
    path('kontrola/', control_center, name='kontrola'),
    path('nalog/', account, name='nalog'),
    path('politika-privatnosti/', privacy_policy, name='politika_privatnosti'),
    path('uslovi-koriscenja/', terms, name='uslovi_koriscenja'),
    path('service-worker.js', service_worker, name='service-worker'),
    path('zdravlje/', health, name='zdravlje'),
    path('push-pretplata/', push_subscribe, name='push_pretplata'),
    path('sophie-govor/', sophie_speech, name='sophie_govor'),
    path('media/<path:path>', protected_media, name='zasticeni_mediji'),
]
