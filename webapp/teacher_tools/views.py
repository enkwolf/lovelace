import os.path
import tempfile
import zipfile

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.utils.translation import ugettext as _

from utils.access import determine_access

from courses.models import ContentPage, FileUploadExerciseReturnFile


def download_answers(request, course_slug, instance_slug, content_slug):
    
    content = ContentPage.objects.get(slug=content_slug)
    
    if not determine_access(request.user, content, responsible_only=True):
        return HttpResponseForbidden(_("Only course main responsible teachers are allowed to download answer files."))
    
    
    files = FileUploadExerciseReturnFile.objects.filter(
        answer__exercise__slug=content_slug,
        answer__instance__course__slug=course_slug,
        answer__instance__slug=instance_slug,
    ).values_list("fileinfo", flat=True)
    
    errors = []
    
    with tempfile.TemporaryFile() as temp_storage:
        with zipfile.ZipFile(temp_storage ,"w") as content_zip:
            for fileinfo in files:
                parts = fileinfo.split("/")
                
                fs_path = os.path.join(getattr(settings, "PRIVATE_STORAGE_FS_PATH", settings.MEDIA_ROOT), fileinfo)
                
                try:
                    content_zip.write(fs_path.encode("utf-8"), "/".join((parts[2], parts[1], parts[3], parts[4])))
                except (IndexError, OSError) as e:
                    errors.append(fileinfo)    
                    
            if errors:
                error_str = "Zipping failed for these files:\n\n" + "\n".join(errors)    
                content_zip.writestr("{}/error_manifest".format(parts[2]), error_str)
            
        temp_storage.seek(0)            
        response = HttpResponse(temp_storage.read(), content_type="application/zip")
    
    response["Content-Disposition"] = "attachment; filename={}_answers.zip".format(content_slug)
    return response
    
    
    
    
        
    
   
    
    
    
