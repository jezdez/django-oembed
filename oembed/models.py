import datetime
from django.db import models
try:
    import json
except ImportError:
    from django.utils import simplejson as json
try:
    from django.utils.timezone import now
except ImportError
    now = datetime.datetime.now
from django.utils.translation import ugettext_lazy as _

JSON = 1
XML = 2
FORMAT_CHOICES = (
    (JSON, "JSON"),
    (XML, "XML"),
)

class ProviderRule(models.Model):
    name = models.CharField(_("name"), max_length=128, null=True, blank=True)
    regex = models.CharField(_("regex"), max_length=2000)
    endpoint = models.CharField(_("endpoint"), max_length=2000)
    format = models.IntegerField(_("format"), choices=FORMAT_CHOICES)

    def __unicode__(self):
        return self.name or self.endpoint


class StoredOEmbed(models.Model):
    match = models.TextField(_("match"))
    max_width = models.IntegerField(_("max width"))
    max_height = models.IntegerField(_("max height"))
    html = models.TextField(_("html"))
    json = models.TextField(_("json"))
    date_added = models.DateTimeField(
        _("date added"), default=now)

    class Meta:
        ordering = ('-max_width',) # larger ones take precedence

    def __unicode__(self):
        return self.match

    def get_json(self, name):
        """ Convenience for JSON properties; e.g. get_json('thumbnail_url') """
        return json.loads(self.json).get(name, None)
