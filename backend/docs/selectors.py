from django.db.models import Q, Case, When, Value, IntegerField

from docs.models import Document


def get_user_documents(user):
    return Document.objects.filter(owner=user)

def get_available_documents(user):
    return Document.objects.filter(
        Q(owner=user) | Q(accesses__user=user)
    ).distinct()

def get_available_documents_sorted(user):
    return get_available_documents(user).alias(
        is_owner=Case(
            When(
                owner=user,
                then=Value(1),
            ),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('-is_owner', '-dt_updated')
