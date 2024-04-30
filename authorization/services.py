import random

from rest_framework_simplejwt.tokens import RefreshToken

from .models import ConfirmationCode
from .utils import EmailUtil

def create_token_and_send_to_email(user):
    code = ''
    for i in range(4):
        code += str(random.randint(0,9))
    try:
        user_code = ConfirmationCode.objects.get(profile = user.user_profile)
    except Exception:
        user_code = ConfirmationCode.objects.create(profile = user.user_profile, code = code)
    else:
        user_code.code = code
        user_code.save()
    data = {'code': user_code.code,
            'email_subject': 'Verify your email',
            'to_email': user.email}
    html = 'authorization/email_mess.html'
    EmailUtil.send_email(data, html)

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }
    
def destroy_token(refresh_token):
    token = RefreshToken(refresh_token)
    token.blacklist()