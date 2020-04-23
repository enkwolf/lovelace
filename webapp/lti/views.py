import json
import redis
import time

from django.conf import settings
from django.views.generic.base import TemplateView, View
from django.template import Template, loader, engines
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect,\
    HttpResponseNotFound, HttpResponseForbidden, HttpResponseNotAllowed,\
    HttpResponseServerError, HttpResponseBadRequest
from django.utils.translation import ugettext as _
from django.utils.decorators import method_decorator
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie

from lti_provider.mixins import LTIAuthMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from cgi import escape

from lovelace.celery import app as celery_app

from courses.models import ContentGraph, Course, CourseInstance, ContentPage, Evaluation
from courses.views import compile_evaluation_data
import courses.markupparser as markupparser
import courses.blockparser as blockparser
from courses.tasks import get_celery_worker_status

from pylti.common import post_message

from reversion.models import Version



class IndexView(TemplateView):
    template_name = "lti/index.html"


class SuccessView(TemplateView):
    template_name = "lti/success.html"
    

class LTITestAssignmentView(LTIAuthMixin, LoginRequiredMixin, TemplateView):

    template_name = "lti/test.html"

    def get_context_data(self, **kwargs):
        return {
            'is_student': self.lti.lis_result_sourcedid(self.request),
            'course_title': self.lti.course_title(self.request),
            'number': 1
        }
    
class LTIAssignmentView(LTIAuthMixin, LoginRequiredMixin, View):
    
    def get(self, request, **kwargs):
        course_slug = request.GET.get("custom_course")
        instance_slug = request.GET.get("custom_instance")
        content_slug = request.GET.get("custom_content")
        try:
            course = Course.objects.get(slug=course_slug)
            if instance_slug == course_slug:
                instance = CourseInstance.objects.get(primary=True, course__slug=course_slug)
            else:
                instance = CourseInstance.objects.get(slug=instance_slug)
            content = ContentPage.objects.get(slug=content_slug)
        except Course.DoesNotExist as e:
            return HttpResponseNotFound(_("Course not found."))
        except CourseInstance.DoesNotExist as e:
            return HttpResponseNotFound(_("Course instance not found."))
        except ContentPage.DoesNotExist as e:
            return HttpResponseNotFound(_("Content not found."))
        
        cg = ContentGraph.objects.get(instance=instance, content=content)
        question = blockparser.parseblock(escape(content.question), {"course": course})
        evaluation = content.get_user_evaluation(content, request.user, instance)
        answer_count = content.get_user_answers(content, request.user, instance).count()
        choices = answers = content.get_choices(content, revision=cg.revision)
        
        context = {
            'course': course,
            'course_slug': course.slug,
            'instance': instance,
            'instance_slug': instance.slug,
            'content': content,
            'enrolled': True,
            'course_staff': False,
            'embedded': False,
            'content_name': content.name,
            'content_type': content.content_type,
            'question': question,
            'choices': choices,
            'evaluation': evaluation,
            'answer_count': answer_count,
            'sandboxed': False,
            'termbank_contents': [],
            'term_div_data': []
        }
        rendered_content = content.rendered_markup(request, context)
        context["rendered_content"] = rendered_content
        
        t = loader.get_template("lti/lti-content.html")
        return HttpResponse(t.render(context, request))
        
@method_decorator(ensure_csrf_cookie, "post")
class LTICheckAnswer(LTIAuthMixin, LoginRequiredMixin, View):

    def message_identifier(self):
        return '{:.0f}'.format(time.time())

    def post(self, request, course, instance, content, revision):
    
        if revision == "head":
            latest = Version.objects.get_for_object(content).latest("revision__date_created")
            revision = latest.revision_id
                
        try:
            content_graph = ContentGraph.objects.get(instance=instance, content=content)
        except ContentGraph.DoesNotExist as e:
            pass
        else:
            if content_graph is not None:
                if not content_graph.deadline or datetime.datetime.now() < content_graph.deadline:
                    pass
                else:
                    # TODO: Use a template!
                    return JsonResponse({
                        'result': _('The deadline for this exercise (%s) has passed. Your answer will not be evaluated!') % (content_graph.deadline)
                    })
        user = request.user
        ip = request.META.get('REMOTE_ADDR')
        answer = request.POST
        files = request.FILES

        exercise = content
        
        try:
            answer_object = exercise.save_answer(content, user, ip, answer, files, instance, revision)
        except InvalidExerciseAnswerException as e:
            return JsonResponse({
                'result': str(e)
            })
        evaluation = exercise.check_answer(content, user, ip, answer, files, answer_object, revision)
        
        if not exercise.manually_evaluated:
            if exercise.content_type == "FILE_UPLOAD_EXERCISE":
                task_id = evaluation["task_id"]
                progress_url = reverse('lovelace_lti:check_progress', kwargs={
                    'course': course,
                    'instance': instance,
                    'content': content,
                    'revision': revision,
                    'task_id': task_id
                })
                return JsonResponse({"state": None, "metadata": None, "redirect": progress_url})

            exercise.save_evaluation(content, user, evaluation, answer_object)
            evaluation["manual"] = False
        else:
            evaluation["manual"] = True
        
        msg_context = {
            'course_slug': course.slug,
            'instance_slug': instance.slug,
            'instance': instance,
            'content_page': content
        }
        
        hints = ["".join(markupparser.MarkupParser.parse(msg, request, msg_context)).strip()
                for msg in evaluation.get('hints', [])]
        
        answer_count = exercise.get_user_answers(exercise, user, instance).count()
        answer_count_str = get_answer_count_meta(answer_count)

        t = loader.get_template("courses/exercise-evaluation.html")
        total_evaluation = exercise.get_user_evaluation(content, user, instance)
        
        if evaluation.get("evaluation"):
            score = 1
            
            xml = self.lti.generate_request_xml(
                self.message_identifier(), 'replaceResult',
                self.lti.lis_result_sourcedid(request),
                score,
                None
            )
            grade_posted = post_message(
                self.lti.consumers(),
                self.lti.oauth_consumer_key(request),
                self.lti.lis_outcome_service_url(request),
                xml
            )
        else:
            grade_posted = False

        data = {
            'result': t.render(evaluation),
            'hints': hints,
            'evaluation': evaluation.get("evaluation"),
            'answer_count_str': answer_count_str,
            'next_instance': evaluation.get('next_instance', None),
            'total_instances': evaluation.get('total_instances', None),
            'total_evaluation': total_evaluation,
            'grade_posted': grade_posted
        }
        
        
        return JsonResponse(data)

@method_decorator(ensure_csrf_cookie, "get")
class LTICheckProgress(LTIAuthMixin, LoginRequiredMixin, View):

    def message_identifier(self):
        return '{:.0f}'.format(time.time())
    
    def get(self, request, course, instance, content, revision, task_id):
        # Based on https://djangosnippets.org/snippets/2898/
        # TODO: Check permissions
        task = celery_app.AsyncResult(id=task_id)
        info = task.info
        if task.ready():
            evaluation = self._get_evaluation(request, course, instance, content, revision, task_id, task)
            if evaluation["evaluation"]:
                score = 1
                
                xml = self.lti.generate_request_xml(
                    self.message_identifier(), 'replaceResult',
                    self.lti.lis_result_sourcedid(request),
                    score,
                    None
                )
                grade_posted = post_message(
                    self.lti.consumers(),
                    self.lti.oauth_consumer_key(request),
                    self.lti.lis_outcome_service_url(request),
                    xml
                )
            else:
                grade_posted = False
                
            evaluation["grade_posted"] = grade_posted
            return JsonResponse(evaluation)
            
        else:
            celery_status = get_celery_worker_status()
            if "errors" in celery_status:
                data = celery_status
            else:
                progress_url = reverse('lovelace_lti:check_progress',
                                    kwargs={'course': course,
                                            'instance': instance,
                                            'content': content,
                                            'revision': revision,
                                            'task_id': task_id,})
                if not info: info = task.info # Try again in case the first time was too early
                data = {"state": task.state, "metadata": info, "redirect": progress_url}
            return JsonResponse(data)

    def _get_evaluation(self, request, course, instance, content, revision, task_id, task):
        evaluation_id = task.get()
        evaluation_obj = Evaluation.objects.get(id=evaluation_id)

        r = redis.StrictRedis(**settings.REDIS_RESULT_CONFIG)
        evaluation_json = r.get(task_id).decode("utf-8")
        evaluation_tree = json.loads(evaluation_json)
        r.delete(task_id)
        task.forget()

        msg_context = {
            'course_slug': course.slug,
            'instance_slug': instance.slug,
            'instance': instance,
            'content_page': content
        }

        data = compile_evaluation_data(request, evaluation_tree, evaluation_obj, msg_context)

        if evaluation_tree['test_tree'].get('errors', []):
            if evaluation_tree['timedout']:
                data['errors'] = _("The program took too long to execute and was terminated. Check your code for too slow solutions.")
            else:
                print(evaluation_tree['test_tree']['errors'])        
                data['errors'] = _("Checking program was unable to finish due to an error. Contact course staff.")
                #print(data)

        return data
    
        
        
        
        
        



def get_answer_count_meta(answer_count):
    # TODO: Maybe refactor
    t = engines['django'].from_string("""{% load i18n %}{% blocktrans count counter=answer_count %}<span class="answer-count">{{ counter }}</span> answer{% plural %}<span class="answer-count">{{ counter }}</span> answers{% endblocktrans %}""")
    return t.render({'answer_count': answer_count})





    