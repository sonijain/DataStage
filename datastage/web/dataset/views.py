import errno
import os
import urllib

from django.contrib.formtools.wizard import FormWizard
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.forms.util import ErrorList
from django_conneg.views import HTMLView, JSONView
from django_conneg.http import HttpResponseSeeOther
import posix1e

import datastage.util.datetime
from datastage.config import settings
from datastage.util.path import get_permissions
from datastage.util.views import RedisView
from datastage.web.dataset.models import DatasetSubmission, Repository, RepositoryUser
from datastage.web.dataset import openers, forms
from datastage.dataset import Dataset, SUBMISSION_QUEUE


class IndexView(HTMLView):
    def get(self, request):
        return self.render(request, {}, 'dataset/index')

class SubmitView(HTMLView, RedisView):
    @method_decorator(login_required)
    def dispatch(self, request):
        return super(SubmitView, self).dispatch(request)

    def common(self, request):
        path = request.REQUEST.get('path')
        if not path:
            raise Http404
        path_parts = path.rstrip('/').split('/')
        path_on_disk = os.path.normpath(os.path.join(settings.DATA_DIRECTORY, *path_parts))
        try:
            permissions = get_permissions(path_on_disk, request.user.username, check_prefixes=True)
        except IOError, e:
            if e.errno == errno.ENOENT:
                raise Http404
            elif e.errno == errno.EACCES:
                raise PermissionDenied
            raise
        if posix1e.ACL_WRITE not in permissions:
            raise PermissionDenied

        try:
            dataset_submission = DatasetSubmission.objects.get(path_on_disk=path_on_disk)
        except DatasetSubmission.DoesNotExist:
            dataset_submission = DatasetSubmission(path_on_disk=path_on_disk)
        dataset_submission.submitting_user = request.user

        form = forms.DatasetSubmissionForm(request.POST or None, instance=dataset_submission)
        
        return {'path': path,
                'form': form,
                'path_on_disk': path_on_disk,
                'dataset_submission': dataset_submission,
                'queued': request.GET.get('queued') == 'true'}


    def get(self, request):
        context = self.common(request)
        if context['dataset_submission'].status not in ('new', 'submitted', 'error'):
            return self.render(request, context, 'dataset/submitted')
        return self.render(request, context, 'dataset/submit')
    
    def post(self, request):
        context = self.common(request)
        form = context['form']

        if form.instance.status not in ('new', 'submitted', 'error'):
            return self.render(request, context, 'dataset/submitted')

        if not form.is_valid():
            return self.render(request, context, 'dataset/submit')
        
        form.save()
        dataset = form.instance.dataset

        cleaned_data = form.cleaned_data

        repository = cleaned_data['repository']
        
        redirect_url = '?%s' % urllib.urlencode({'path': context['path'],
                                                 'queued': 'true'})
        
        
        try:
            opener = openers.get_opener(repository, request.user)
            form.instance.remote_url = dataset.preflight_submission(opener, repository)
        except openers.SimpleCredentialsRequired:
            url = '%s?%s' % (
                reverse('dataset:simple-credentials'),
                urllib.urlencode({'next': '%s?%s' % (request.path, urllib.urlencode({'path': context['path'],
                                                                                     'repository': repository.id})),
                                  'repository': repository.id}),
            )
            return HttpResponseSeeOther(url)
        except Dataset.DatasetIdentifierRejected, e:
            form.errors['identifier'] = ErrorList([unicode(e)])
            return self.render(request, context, 'dataset/submit')
            
        else:
            form.instance.status = 'queued'
        
            self.redis.rpush(SUBMISSION_QUEUE, self.pack(form.instance.id))
            form.instance.queued_at = datastage.util.datetime.now()
            form.instance.save()
        
        
        return HttpResponseSeeOther(redirect_url)

class SimpleCredentialsView(HTMLView):
    def common(self, request):
        repository = get_object_or_404(Repository, id=request.GET.get('repository'))
        repository_user, _ = RepositoryUser.objects.get_or_create(repository=repository, user=request.user)
        return {'repository': repository,
                'repository_user': repository_user,
                'form': forms.SimpleCredentialsForm(request.POST or None,
                                                    initial={'username': repository_user.username,
                                                             'next': request.REQUEST.get('next')})}

    def get(self, request):
        context = self.common(request)
        return self.render(request, context, 'dataset/simple-credentials')
    
    def post(self, request):
        context = self.common(request)
        if not context['form'].is_valid():
            return self.render(request, context, 'dataset/simple-credentials')
        
        cleaned_data = context['form'].cleaned_data
        context['repository_user'].username = cleaned_data['username']
        context['repository_user'].password = cleaned_data['password']
        context['repository_user'].save()
        
        return HttpResponseSeeOther(cleaned_data['next'])
            

class DatasetSubmissionView(HTMLView):
    def get(self, request, id):
        dataset_submission = get_object_or_404(DatasetSubmission, id=id)
        context = {'dataset_submission': dataset_submission}
        return self.render(request, context, 'dataset/submission-detail')

#class SubmitWizard(HTMLView, JSONView, CookieWizardView):
#    pass