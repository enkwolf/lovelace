import re

from courses.models import ContentGraph, EmbeddedLink, CourseMediaLink, TermToInstanceLink, InstanceIncludeFileToInstanceLink
from django.utils.text import slugify as slugify
from reversion.models import Version

def first_title_from_content(content_text):
    """
    Finds the first heading from a content page and returns the title. Also
    return the slugified anchor.
    """

    titlepat = re.compile("(?P<level>={1,6}) ?(?P<title>.*) ?(?P=level)")
    try:
        title = titlepat.findall(content_text)[0]
    except IndexError:
        title = ""
        anchor = ""
    else:
        anchor = slugify(title, allow_unicode=True)

    return title, anchor

def get_course_instance_tasks(instance, deadline_before=None):

    all_embedded_links = EmbeddedLink.objects.filter(instance=instance).order_by("embedded_page__name")

    task_pages = []

    content_links = ContentGraph.objects.filter(instance=instance, scored=True, visible=True).order_by("ordinal_number")
    if deadline_before is not None:
        content_links = content_links.filter(deadline__lt=deadline_before)

    for content_link in content_links:
        page_task_links = all_embedded_links.filter(parent=content_link.content)
        if page_task_links:
            task_pages.append((content_link.content, page_task_links))

    return task_pages

def get_instance_revision(model_class, instance_id, revision):
    print(revision)
    instance_obj = model_class.objects.get(id=instance_id)
    if revision is not None:
        return Version.objects.get_for_object(instance_obj).get(revision=revision)._object_version.object
    return instance_obj

def compile_json_feedback(log):
    # render all individual messages in the log tree
    triggers = []
    hints = []

    for test in log:
        test["title"] = "".join(markupparser.MarkupParser.parse(test["title"], request, context)).strip()
        test["runs"].sort(key=lambda run: run["correct"])
        for run in test["runs"]:
            for output in run["output"]:
                output["msg"] = "".join(markupparser.MarkupParser.parse(output["msg"], request, context)).strip()
                triggers.extend(output.get("triggers", []))
                hints.extend(
                    "".join(markupparser.MarkupParser.parse(msg, request, context)).strip()
                    for msg in output.get("hints", [])
                )

    t_messages = loader.get_template('courses/exercise-evaluation-messages.html')
    feedback = {
        'messages': t_messages.render({'log': log}),
        'hints': hints,
        'triggers': triggers
    }
    return feedback

