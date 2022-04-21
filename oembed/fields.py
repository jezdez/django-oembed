import re

from django.core import exceptions
from django.db import models

from .models import ProviderRule

class OEmbedField(models.URLField):
    """
    A URL pointing to an oEmbed provider.
    
    See http://www.oembed.com/ for information on providers
    """
    
    description = "A URL pointing to an oEmbed provider"
    
    def validate(self, value, model_instance):
        for pattern in ProviderRule.objects.values_list('regex', flat=True):
            if re.match(pattern, value):
                return
        raise exceptions.ValidationError('Not a valid oEmbed link')


try:
    from south.modelsinspector import add_introspection_rules
except ImportError:
    pass # No south, nevermind
else:
    # Tell south to treat OEmbedFields just like URLFields
    rules = ['^%s\.OEmbedField' % (__name__.replace('.','\.'),)]
    add_introspection_rules([], rules)
