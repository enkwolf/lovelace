import django.conf

from courses.models import *

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin, GroupAdmin

from django.core.cache import cache
from django.urls import reverse

from django.db import models, transaction
from django.db.models import Q
from django.forms import Field, ModelForm, TextInput, Textarea, ModelChoiceField, BaseInlineFormSet

from .forms import FileEditForm, RepeatedTemplateExerciseBackendForm, ContentForm, TextfieldAnswerForm, InstanceForm
from .widgets import AdminFileWidget, AdminTemplateBackendFileWidget

from modeltranslation.admin import TranslationAdmin, TranslationTabularInline, \
    TranslationStackedInline

from reversion.admin import VersionAdmin
from reversion.models import Version
from reversion import revisions as reversion

from utils.management import CourseContentAccess, CourseMediaAccess

# Moved these here from models.py so that all registering happens
# in this file (as VersionAdmin autoregisters the associated model)
# This makes modeltranslation work for with reversion, probably due 
# to translated fields being added between loading models.py and 
# this module.
reversion.register(ContentPage)
reversion.register(Hint)
reversion.register(FileExerciseTest, follow=['fileexerciseteststage_set'])
reversion.register(FileExerciseTestStage, follow=['fileexercisetestcommand_set'])
reversion.register(FileExerciseTestCommand, follow=['fileexercisetestexpectedoutput_set'])
reversion.register(FileExerciseTestExpectedOutput)
reversion.register(FileExerciseTestExpectedStdout)
reversion.register(FileExerciseTestExpectedStderr)
reversion.register(InstanceIncludeFileToExerciseLink)
reversion.register(InstanceIncludeFile)
reversion.register(FileExerciseTestIncludeFile)
reversion.register(IncludeFileSettings)
reversion.register(TextfieldExerciseAnswer)
reversion.register(MultipleChoiceExerciseAnswer)
reversion.register(CourseMedia)
reversion.register(TermTab)
reversion.register(TermLink)
reversion.register(CheckboxExerciseAnswer)
reversion.register(CodeInputExerciseAnswer)
reversion.register(CodeReplaceExerciseAnswer)
reversion.register(RepeatedTemplateExerciseTemplate)
reversion.register(RepeatedTemplateExerciseBackendFile)
reversion.register(RepeatedTemplateExerciseBackendCommand)


## User profiles
# http://stackoverflow.com/questions/4565814/django-user-userprofile-and-admin
admin.site.unregister(User)
admin.site.unregister(Group)


class UserProfileInline(admin.StackedInline):
    model = UserProfile

class UserProfileAdmin(UserAdmin):
    inlines = [UserProfileInline,]

admin.site.register(User, UserProfileAdmin)

class CopyingGroupAdmin(GroupAdmin):
    save_as = True

admin.site.register(Group, CopyingGroupAdmin)

## Feedback for user answers
#admin.site.register(Evaluation)

## Exercise types
# TODO: Create an abstract way to admin the different task types
#class AbstractQuestionAdmin(admin.ModelAdmin):
#    def save_model(self, request, obj, form, change):
#        obj.save()
#        if not change:
#            obj.users.add(request, user)
#
##    def queryset(self, request):
#        qs = super(AbstractQuestionAdmin, self).queryset(request)
#        if request.user.is_superuser:
#            return qs.select_subclasses()
#        return qs.select_subclasses().filter(users=request.user)

# TODO: How to link ContentFeedbackQuestion objects nicely?
class HintInline(TranslationTabularInline):
    model = Hint
    fk_name = 'exercise'
    extra = 0
    queryset = TranslationTabularInline.get_queryset


class SoftDeleteFormSet(BaseInlineFormSet):
    
    def delete_existing(self, obj, commit=True):
        if commit:
            obj.exercise = None
            obj.save()
        
class MultipleChoiceExerciseAnswerInline(TranslationTabularInline):
    model = MultipleChoiceExerciseAnswer
    extra = 1
    formset = SoftDeleteFormSet 

class MultipleChoiceExerciseAdmin(CourseContentAccess, TranslationAdmin, VersionAdmin):
    
    content_type = "MULTIPLE_CHOICE_EXERCISE"
    form = ContentForm
    
    #def get_queryset(self, request):
    #    return self.model.objects.filter(content_type="MULTIPLE_CHOICE_EXERCISE")

    fieldsets = [
        ('Page information',   {'fields': ['name', 'slug', 'content', 'question', 'tags'],}),
        ('Exercise miscellaneous', {'fields': ['default_points', 'evaluation_group'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    inlines = [MultipleChoiceExerciseAnswerInline, HintInline]
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500
    save_on_top = True



class CheckboxExerciseAnswerInline(TranslationTabularInline):
    model = CheckboxExerciseAnswer
    extra = 1
    formset = SoftDeleteFormSet

class CheckboxExerciseAdmin(CourseContentAccess, TranslationAdmin, VersionAdmin):
    
    content_type = "CHECKBOX_EXERCISE"
    form = ContentForm
    
    #def get_queryset(self, request):
    #   return self.model.objects.filter(content_type="CHECKBOX_EXERCISE")

    fieldsets = [
        ('Page information',   {'fields': ['name', 'slug', 'content', 'question', 'tags']}),
        ('Exercise miscellaneous', {'fields': ['default_points', 'evaluation_group'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    inlines = [CheckboxExerciseAnswerInline, HintInline]
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500
    save_on_top = True





class TextfieldExerciseAnswerInline(TranslationStackedInline):
    model = TextfieldExerciseAnswer
    extra = 1
    form = TextfieldAnswerForm
    
    

class TextfieldExerciseAdmin(CourseContentAccess, TranslationAdmin, VersionAdmin):
    
    content_type = "TEXTFIELD_EXERCISE"
    form = ContentForm
    
    #def get_queryset(self, request):
    #    return self.model.objects.filter(content_type="TEXTFIELD_EXERCISE")

    fieldsets = [
        ('Page information',   {'fields': ['name', 'slug', 'content', 'question', 'tags']}),
        ('Exercise miscellaneous', {'fields': ['default_points', 'evaluation_group'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    inlines = [TextfieldExerciseAnswerInline, HintInline]
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500
    save_on_top = True

class CodeReplaceExerciseAnswerInline(admin.StackedInline):
    model = CodeReplaceExerciseAnswer
    extra = 1

class CodeReplaceExerciseAdmin(CourseContentAccess, TranslationAdmin, VersionAdmin):
    
    content_type = "CODE_REPLACE_EXERCISE"
    
    #def get_queryset(self, request):
    #    return self.model.objects.filter(content_type="CODE_REPLACE_EXERCISE")

    fieldsets = [
        ('Page information',   {'fields': ['name', 'slug', 'content', 'question', 'tags']}),
        ('Exercise miscellaneous', {'fields': ['default_points', 'evaluation_group'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    inlines = [CodeReplaceExerciseAnswerInline, HintInline]
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500
    save_on_top = True

class RepeatedTemplateExerciseTemplateInline(TranslationStackedInline):
    model = RepeatedTemplateExerciseTemplate
    extra = 1

class RepeatedTemplateExerciseBackendFileInline(admin.StackedInline):
    model = RepeatedTemplateExerciseBackendFile
    extra = 1
    form = RepeatedTemplateExerciseBackendForm
    formfield_overrides = {
        models.FileField: {'widget': AdminTemplateBackendFileWidget}
    }

class RepeatedTemplateExerciseBackendCommandInline(TranslationStackedInline):
    model = RepeatedTemplateExerciseBackendCommand

class RepeatedTemplateExerciseAdmin(CourseContentAccess, TranslationAdmin, VersionAdmin):

    content_type = "REPEATED_TEMPLATE_EXERCISE"
    form = ContentForm

    fieldsets = [
        ('Page information',   {'fields': ['name', 'slug', 'content', 'question', 'tags']}),
        ('Exercise miscellaneous', {'fields': ['default_points', 'evaluation_group'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]

    inlines = [RepeatedTemplateExerciseTemplateInline, RepeatedTemplateExerciseBackendFileInline,
               RepeatedTemplateExerciseBackendCommandInline, HintInline]
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500
    save_on_top = True

class FileExerciseTestCommandAdmin(admin.TabularInline):
    model = FileExerciseTestCommand
    extra = 1

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super(FileExerciseTestCommandAdmin, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'command_line':
            formfield.widget = TextInput(attrs={'size':120})
        return formfield

class FileExerciseTestExpectedStdoutAdmin(admin.StackedInline):
    model = FileExerciseTestExpectedStdout
    extra = 0
    fields = (('expected_answer', 'hint'), 'correct', 'regexp', 'videohint')

class FileExerciseTestExpectedStderrAdmin(admin.StackedInline):
    model = FileExerciseTestExpectedStderr
    extra = 0
    fields = (('expected_answer', 'hint'), 'correct', 'regexp', 'videohint')

# class FileExerciseTestAdmin(admin.ModelAdmin):
#     fieldsets = (
#         ('General settings', {
#             'fields': ('task', 'name', 'inputs')
#         }),
#         ('Advanced settings', {
#             'classes': ('collapse',),
#             'fields': ('timeout', 'signals', 'retval')
#         }),
#     )
#     inlines = []
#     search_fields = ("name",)
#     list_display = ("name", "exercise")
#     list_per_page = 500
    
#     def formfield_for_foreignkey(self, db_field, request, **kwargs):
#         if db_field.name == "exercise":
#             kwargs["queryset"] = FileUploadExercise.objects.order_by("name")
#         return super(FileExerciseTestAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

#class FileExerciseTestAdmin(admin.StackedInline):
#    inlines = [FileExerciseTestCommandAdmin, FileExerciseTestExpectedOutputAdmin, FileExerciseTestExpectedErrorAdmin, FileExerciseTestIncludeFileAdmin]


class LectureAdmin(CourseContentAccess, TranslationAdmin, VersionAdmin):
    
    content_type = "LECTURE"
    form = ContentForm
    fieldsets = [
        ('Page information',    {'fields': ['name', 'content']}),
        ('Feedback',            {'fields': ['feedback_questions']})
    ]
    
    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super(LectureAdmin, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name in ('content'):
            formfield.widget = Textarea(attrs={'rows':25, 'cols':120})
        elif db_field.name == 'tags':
            formfield.widget = Textarea(attrs={'rows':2})
        return formfield

    # TODO: instanceless viewing doesn't work
    #def view_on_site(self, obj):
    #    return reverse('courses:sandbox', kwargs={'content_slug': obj.slug})

    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500
    save_on_top = True

# Still required even though a custom admin is implemented
class FileUploadExerciseAdmin(CourseContentAccess, TranslationAdmin, VersionAdmin):
    
    content_type = "FILE_UPLOAD_EXERCISE"
    form = ContentForm
    
    #def get_queryset(self, request):
    #    return self.model.objects.filter(content_type="FILE_UPLOAD_EXERCISE")
    
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500

admin.site.register(FileUploadExercise, FileUploadExerciseAdmin)

# TODO: Use the view_on_site on all content models!

admin.site.register(Lecture, LectureAdmin)
admin.site.register(MultipleChoiceExercise, MultipleChoiceExerciseAdmin)
admin.site.register(CheckboxExercise, CheckboxExerciseAdmin)
admin.site.register(TextfieldExercise, TextfieldExerciseAdmin)
#admin.site.register(CodeReplaceExercise, CodeReplaceExerciseAdmin)
admin.site.register(RepeatedTemplateExercise, RepeatedTemplateExerciseAdmin)

admin.site.register(FileExerciseTestIncludeFile)
admin.site.register(InstanceIncludeFile)
admin.site.register(IncludeFileSettings)

    ## Page embeddable objects
class CalendarDateAdmin(admin.StackedInline):
    model = CalendarDate
    extra = 1
    #form = CalendarDateForm

class CalendarAdmin(admin.ModelAdmin):
    inlines = [CalendarDateAdmin]
    search_fields = ("name",)


class FileAdmin(CourseMediaAccess, TranslationAdmin, VersionAdmin):

    search_fields = ('name',)
    form = FileEditForm
    formfield_overrides = {
        models.FileField: {'widget': AdminFileWidget}
    }

class ImageAdmin(CourseMediaAccess, TranslationAdmin, VersionAdmin):

    search_fields = ('name',)
    list_display = ('name', 'description',)
    list_per_page = 500

class VideoLinkAdmin(CourseMediaAccess, TranslationAdmin, VersionAdmin):

    search_fields = ('name',)
    list_display = ('name', 'description',)
    list_per_page = 500

class TermTabInline(TranslationTabularInline):
    model = TermTab
    extra = 0

class TermLinkInline(TranslationTabularInline):
    model = TermLink
    extra = 0
    
    

        
class TermAdmin(TranslationAdmin, VersionAdmin):
    search_fields = ('name',)
    list_display = ('name', 'course',)
    list_filter = ('course',)
    list_per_page = 500
    ordering = ('name',)

    inlines = [TermTabInline, TermLinkInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs
        
        edited = Version.objects.get_for_model(Term).filter(revision__user=request.user).values_list("object_id", flat=True)
        
        return qs.filter(
            Q(id__in=list(edited)) |
            Q(course__staff_group__user=request.user)
        ).distinct()

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        elif request.user.is_staff:
            if obj:
                return Version.objects.get_for_object(obj).filter(revision__user=request.user).exists() or request.user in obj.course.staff_group.user_set.get_queryset()
            else:
                return True
        else:
            return False
        
    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        elif request.user.is_staff:
            if obj:
                return Version.objects.get_for_object(obj).filter(revision__user=request.user).exists() or request.user in obj.course.staff_group.user_set.get_queryset()
            else:
                return True
        else:
            return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        lang_list = django.conf.settings.LANGUAGES
        for instance in CourseInstance.objects.filter(course=obj.course):       
            instance_slug = instance.slug
            for lang, _ in lang_list:
                cache.set('termbank_contents_{instance}_{lang}'.format(instance=instance_slug, lang=lang), None)
                cache.set('termbank_div_data_{instance}_{lang}'.format(instance=instance_slug, lang=lang), None)
                
        
        

admin.site.register(Calendar, CalendarAdmin)
admin.site.register(File, FileAdmin)
admin.site.register(Image, ImageAdmin)
admin.site.register(VideoLink, VideoLinkAdmin)
admin.site.register(Term, TermAdmin)


## Course related administration
class ContentGraphAdmin(admin.ModelAdmin):
    
    search_fields = ('content__name',)
    list_display = ('ordinal_number', 'content', 'instance',)
    list_display_links = ('content',)
    list_filter = ('instance',)
    list_per_page = 500
    ordering = ('instance', 'ordinal_number',)
    
    fields = ('parentnode', 'content', 'deadline', 'scored', 'ordinal_number', 'visible')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Limit the queryset for content selector to pages that are in the 
        editor's access chain. 
        """
        
        if db_field.name == 'content':
            kwargs['queryset'] = CourseContentAccess.content_access_list(request, ContentPage)
            
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
        
    def get_queryset(self, request):
        return super(ContentGraphAdmin, self).get_queryset(request)
    
    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        elif request.user.is_staff:
            if obj:
                return self._match_groups(request.user, obj)            
            else:
                return True
        else:
            return False
        
    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        elif request.user.is_staff:
            if obj:
                return self._match_groups(request.user, obj)
            else:
                return True
        else:
            return False
        
    def _match_groups(self, user, obj):
        user_groups = user.groups.get_queryset()
        
        if Course.objects.filter(courseinstance__contents=obj).filter(staff_group__in=user_groups):
            return True
        
        return False

    def get_instances(self, obj):
        return " | ".join([i.name for i in obj.courseinstance_set.all()])
    
    get_instances.short_description = "Instances"

admin.site.register(ContentGraph, ContentGraphAdmin)

class CourseAdmin(TranslationAdmin, VersionAdmin):
    fieldsets = [
        (None,             {'fields': ['name', 'slug',]}),
        ('Course outline', {'fields': ['description', 'code', 'credits']}),
        ('Administration', {'fields': ['staff_group', 'main_responsible']}),
        #('Settings for start date and end date of the course', {'fields': ['start_date','end_date'], 'classes': ['collapse']}),
    ]
    #formfield_overrides = {models.ManyToManyField: {'widget':}}
    search_fields = ('name',)
    readonly_fields = ('slug',)

admin.site.register(Course, CourseAdmin)

class ContentGraphInline(admin.TabularInline):
    model = ContentGraph
    extra = 0
    fields = ('parentnode', 'content', 'deadline', 'scored', 'ordinal_number', 'visible', 'revision')
    readonly_fields = ('revision', )
    

class CourseInstanceAdmin(TranslationAdmin, VersionAdmin):
    """
    NOTE: Only the user designated as main responsible for a course is 
    allowed to create instances of the course, and to include content 
    graphs to an instance. 
    """    
    
    fieldsets = [
        (None,                {'fields': ['name', 'email', 'course', 'frontpage']}),
        ('Schedule settings', {'fields': ['start_date', 'end_date', 'active', 'visible', 'primary']}),
        ('Enrollment',        {'fields': ['manual_accept']}),
        ('Content license',   {'fields': ['content_license', 'license_url']}),
        ('Instance outline',  {'fields': ['frozen']}),
    ]
    search_fields = ('name',)
    list_display = ('name', 'course')
    save_as = True
    form = InstanceForm

    inlines = [ContentGraphInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Only show courses where the editor is marked as main responsible. 
        """
        
        if db_field.name == 'course':
            if not request.user.is_superuser:
                kwargs['queryset'] = Course.objects.filter(main_responsible=request.user)
            
        return super().formfield_for_foreignkey(db_field, request, **kwargs)                                                
        
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        Only show content graphs that contain content that is in the editor's
        access chain.
        """
        
        if db_field.name == 'contents':           
            content_access = CourseContentAccess.content_access_list(request, ContentPage)
            kwargs['queryset'] = ContentGraph.objects.filter(content__in=content_access)
            
        return super().formfield_for_manytomany(db_field, request, **kwargs)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs
        
        return qs.filter(course__main_responsible=request.user)
        
    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        elif request.user.is_staff:
            if obj:
                return obj.course.main_responsible == request.user
            else:
                return True
        else:
            return False
        
    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        elif request.user.is_staff:
            if obj:
                return obj.course.main_responsible == request.user
            else:
                return True
        else:
            return False
        
    def save_model(self, request, obj, form, change):
        self._new = False
        if obj.pk == None:
            self._new = True
        
        super().save_model(request, obj, form, change)
        
        if self._new:
            instance_files = InstanceIncludeFile.objects.filter(course=obj.course)
            for ifile in instance_files:
                link = InstanceIncludeFileToInstanceLink(
                    revision=None,
                    include_file=ifile,
                    instance=obj
                )
                link.save()
                
            terms = Term.objects.filter(course=obj.course)
            for term in terms:
                link = TermToInstanceLink(
                    revision=None,
                    term=term,
                    instance=obj
                )
                link.save()
            
        self.current = obj
        transaction.on_commit(self.finish_cg)
            
    # the horror
    def finish_cg(self): 
        obj = self.current
        if obj.frontpage:
            fp_node = ContentGraph.objects.filter(courseinstance=obj.id, ordinal_number=0).first()
            if fp_node and not self._new:
                fp_node.content = obj.frontpage
                fp_node.save()
            else:
                if fp_node:
                    fp_node.delete()
                fp_node = ContentGraph(
                    content=obj.frontpage,
                    instance=obj,
                    scored=False,
                    ordinal_number=0
                )

        if not obj._was_frozen and obj.frozen:
            obj._was_frozen = True
            obj.freeze()
        else:
            for cg in ContentGraph.objects.filter(instance=obj):
                cg.content.update_embedded_links(obj, cg.revision)
            
admin.site.register(CourseInstance, CourseInstanceAdmin)
    