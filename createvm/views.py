#coding=utf-8
from django.shortcuts import render,get_object_or_404,render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.template import RequestContext
from django_ajax.decorators import ajax
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from blockmanager.views import get_config

import string
import ansible.runner
import ConfigParser
import uuid
from lxml import etree
import random
import logging
import logging.config

from keystoneclient.auth.identity import v2
from keystoneclient import session
from novaclient import client
from keystoneclient.v2_0 import client as keystoneClient
# Create your views here.

# Create your views here.


def login(request):
	try:
		if request.method == 'GET':
			return render(request,'createvm/login.html')
		#判断验证码
		check_code = request.POST.get('check_code', None)
		code = request.POST.get('code', None)
		if check_code.lower() != code.lower():
			raise ValueError('验证码错误')

		username = request.POST.get('username', None)
		password = request.POST.get('password', None)
		if username == None or password == None:
			raise ValueError('input lack')
		tenant_name = username
		configs = get_config()
		auth_url = configs['auth_url'] 

		auth = v2.Password(auth_url=auth_url, username=username, 
				password=password, tenant_name=tenant_name)
		sess = session.Session(auth=auth)
		nova = client.Client('2', session=sess)
		nova.servers.list()

		request.session['username'] = username
		request.session['password'] = password
		request.session['tenant_name'] = tenant_name
		request.session['auth_url'] = auth_url

		return HttpResponseRedirect(reverse('createvm:index'))
	except Exception,e:
		name = request.session.get('username', 'root')
		logger = getLogger(name)
		logger.error(e)
		return HttpResponse(e)


def register(request):
	try:
		if request.method == 'GET':
			return render(request, 'createvm/register.html')
		
		if request.method == 'POST':
			check_code = request.POST.get('check_code', None)
			code = request.POST.get('code', None)
			if code.lower() != check_code.lower():
				raise ValueError('验证码错误')

			username = request.POST.get('username', None)
			password = request.POST.get('password', None)
			check_password = request.POST.get('check_password', None)
			email = request.POST.get('email', None)
			code = request.POST.get('code', None)
			check_code = request.POST.get('check_code', None)
			if username == '' or password == '' or check_password == '' or email == '' or code == '':
				raise ValueError('缺少输入')


			if password != check_password:
				raise ValueError('两次密码不一样')

			configs = get_config()
			keystone = keystoneClient.Client(auth_url=configs['auth_url'], username=configs['username'],
						password=configs['password'], tenant_name=configs['tenant_name'])
			keystone.tenants.create(tenant_name=username,
										description=username + " Tenant", enabled=True)
			tenants = keystone.tenants.list()
			my_tenant = [x for x in tenants if x.name==username][0]
			my_user = keystone.users.create(name=username,
							password=password, tenant_id=my_tenant.id, email=email)

			return HttpResponseRedirect(reverse('createvm:login'))

	except Exception,e:
		return HttpResponse(e)



def logout(request):
	try:
		request.session['username'] = None
		request.session['password'] = None
		request.session['tenant_name'] = None
		return HttpResponseRedirect(reverse('createvm:login'))
	except Exception,e:
		return HttpResponse(e)
	


def index(request):
	try:
		if request.session.get('username', None) == None:
			return HttpResponseRedirect(reverse('createvm:login'))

		username = request.session['username']
		password = request.session['password']
		tenant_name = request.session['tenant_name']
		auth_url = request.session['auth_url']
		auth = v2.Password(auth_url=auth_url, username=username, 
					password=password, tenant_name=tenant_name)
		sess = session.Session(auth=auth)
		nova = client.Client('2', session=sess)
		vms = []
		for ins in nova.servers.list():
			flavor_id = ins.flavor.get('id')
			image_id = ins.image.get('id')
			flavor = nova.flavors.find(id=flavor_id)
			image = nova.images.find(id=image_id)
			if ins.status == 'ACTIVE':
				vnc_url = ins.get_vnc_console('novnc').get('console').get('url')
			else:
				vnc_url = ''
			vm = {'vcups':flavor.vcpus, 'ram':flavor.ram, 'os': image.name, 'name': ins.name, 
					'status':ins.status, 'vnc_url':vnc_url}
			vms.append(vm)

		return render(request,'createvm/index.html', {'vms':vms, 'username':username})

	except Exception, e:
		return HttpResponse(e)


def create(request):
	try:
		if request.session.get('username', None) == None:
			return HttpResponseRedirect(reverse('createvm:login'))
		username = request.session['username']
		password = request.session['password']
		tenant_name = request.session['tenant_name']
		auth_url = request.session['auth_url']
		auth = v2.Password(auth_url=auth_url, username=username, 
					password=password, tenant_name=tenant_name)
		sess = session.Session(auth=auth)
		nova = client.Client('2', session=sess)
		if request.method == 'GET':
			images = nova.images.list()
			return render(request,'createvm/create.html', {'images': images})

		if request.method == 'POST':
			ram = request.POST.get('ram')
			if ram == None:
				raise ValueError('ram is None')
			if 'G' in ram:
				ram = int(ram[:-1]) * 1024
			else:
				ram = int(ram[:-1])
			vcpus = request.POST.get('vcpus')
			if vcpus == None:
				raise ValueError('ram is None')
			vcpus = int(vcpus)
			os = request.POST.get('os')
			if nova.images.find(name=os) == None:
				raise ValueError('choose os')
			vm_name = request.POST.get('vm_name')
			if vm_name == None or vm_name == '':
				raise ValueError('enter a vm name')
			if os == None:
				raise ValueError('choose os')
			number = request.POST.get('number')
			if number == None or number == '0':
				raise ValueError('vm number is error')
			number = int(number)

			flavor = nova.flavors.find(vcpus=vcpus, ram=ram)
			image = nova.images.find(name=os)
			nics = [{'net-id': nova.networks.list()[0].id}]
			for i in range(number):
				nova.servers.create(vm_name, flavor=flavor.id, image=image.id, nics=nics)
			return HttpResponseRedirect(reverse('createvm:index'))
	except Exception, e:
		return HttpResponse(e)


def getLogger(name):
	try:
		if name == '' or name == None:
			name = ''

		logging.config.fileConfig('blockmanager/log.conf')
		logger = logging.getLogger(name)
		return logger
	except Exception,e:
		return HttpResponse(e)