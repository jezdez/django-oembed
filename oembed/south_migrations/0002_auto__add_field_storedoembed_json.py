# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'StoredOEmbed.json'
        db.add_column('oembed_storedoembed', 'json', self.gf('django.db.models.fields.TextField')(default=''), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'StoredOEmbed.json'
        db.delete_column('oembed_storedoembed', 'json')


    models = {
        'oembed.providerrule': {
            'Meta': {'object_name': 'ProviderRule'},
            'endpoint': ('django.db.models.fields.CharField', [], {'max_length': '2000'}),
            'format': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'regex': ('django.db.models.fields.CharField', [], {'max_length': '2000'})
        },
        'oembed.storedoembed': {
            'Meta': {'object_name': 'StoredOEmbed'},
            'date_added': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'html': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'json': ('django.db.models.fields.TextField', [], {}),
            'match': ('django.db.models.fields.TextField', [], {}),
            'max_height': ('django.db.models.fields.IntegerField', [], {}),
            'max_width': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['oembed']
