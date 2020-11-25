from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.template import loader

from filmdemocracy.settings import DEFAULT_FROM_EMAIL


class SpamHelper:

    def __init__(self, request, subject_template_name, email_template_name, html_email_template_name):
        self.request = request
        self.use_https = self.request.is_secure()
        self.from_email = DEFAULT_FROM_EMAIL
        self.subject_template_name = subject_template_name
        self.email_template_name = email_template_name
        self.html_email_template_name = html_email_template_name
        self.domain_override = None
        self.default_context = self.get_default_context()

    def get_default_context(self):
        default_context = {'user': self.request.user,
                           'protocol': 'https' if self.use_https else 'http'}
        if not self.domain_override:
            current_site = get_current_site(self.request)
            default_context['current_site'] = get_current_site(self.request)
            default_context['site_name'] = current_site.name
            default_context['domain'] = current_site.domain
        else:
            default_context['site_name'] = default_context['domain'] = self.domain_override
        return default_context

    def send_emails(self, to_emails_list, email_context=None):
        context = {**self.default_context, **email_context}
        subject = loader.render_to_string(self.subject_template_name, context)
        # http://nyphp.org/phundamentals/8_Preventing-Email-Header-Injection
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string(self.email_template_name, context)
        for to_email in to_emails_list:
            email_messages = EmailMultiAlternatives(subject, body, self.from_email, [to_email])
            if self.html_email_template_name:
                html_email = loader.render_to_string(self.html_email_template_name, context)
                email_messages.attach_alternative(html_email, 'text/html')
            email_messages.send()
