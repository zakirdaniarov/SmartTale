import random

from rest_framework_simplejwt.tokens import RefreshToken

from .models import ConfirmationCode
from .utils import EmailUtil

def create_token_and_send_to_email(user):
    code = ''
    for i in range(4):
        code += str(random.randint(0,9))
    code, _ = ConfirmationCode.objects.update_or_create(profile = user.user_profile, code = code)
    data = {'code': code.code,
            'email_subject': 'Verify your email',
            'to_email': user.email}
    html = 'authorization/email_mess.html'
    EmailUtil.send_email(data, html)

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh_token': str(refresh),
        'access_token': str(refresh.access_token),
    }