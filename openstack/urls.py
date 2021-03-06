from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'openstack.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^blockmanager/', include('blockmanager.urls', namespace='blockmanager')),
    url(r'^createvm/', include('createvm.urls', namespace='createvm')),
)
