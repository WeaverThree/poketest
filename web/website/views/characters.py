
import re
from collections import OrderedDict


from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.encoding import iri_to_uri
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import ListView
from django.views.generic.base import RedirectView

from evennia.utils import class_from_module
from evennia.web.website import forms

from evennia.web.website.views.mixins import TypeclassMixin
from evennia.web.website.views.objects import (
    ObjectCreateView,
    ObjectDeleteView,
    ObjectDetailView,
    ObjectUpdateView,
)

from evennia.web.website.views.characters import CharacterMixin

from world.utils import split_on_all_newlines

_MULTI_NEWLINE_RE = re.compile(r"\|/|\n")
_TAB_RE = re.compile(r"\|-")
_SPACE_RE = re.compile(r"\|_")

class CharacterListView(LoginRequiredMixin, CharacterMixin, ListView):
    """
    This view provides a mechanism by which a logged-in player can view a list
    of all other characters.

    This view requires authentication by default as a nominal effort to prevent
    human stalkers and automated bots/scrapers from harvesting data on your users.

    """

    # -- Django constructs --
    template_name = "website/character_list.html"
    paginate_by = 0

    # -- Evennia constructs --
    page_title = "Character List"
    access_type = "view"

    def get_queryset(self):
        """
        This method will override the Django get_queryset method to return a
        list of all characters (filtered/sorted) instead of just those limited
        to the account.

        Returns:
            queryset (QuerySet): Django queryset for use in the given view.

        """
        account = self.request.user

        out = []


        for obj in sorted(self.typeclass.objects.all(), key=lambda o: (o.faction, o.name)):
            if not obj.access(account, self.access_type):
                continue
            
            if not obj.is_typeclass("typeclasses.characters.PlayerCharacter"):
                continue

            # Filter out unconfigured accounts

            if not obj.accepted_rules:
                continue
            if not obj.species:
                continue
            

            # Filter out superuser

            if obj.has_account and obj.account.is_superuser:
                continue
            elif obj.last_puppeted_by and obj.last_puppeted_by.is_superuser:
                continue
            
            out.append(obj)
            
        return out
    



class CharacterDetailView(CharacterMixin, ObjectDetailView):
    """
    This view provides a mechanism by which a user can view the attributes of
    a character, owned by them or not.

    """

    # -- Django constructs --
    template_name = "website/character.html"

    # -- Evennia constructs --
    # What attributes to display for this object
    attributes = ["name", 'faction', 'rank', 'short_desc', "desc"]
    access_type = "view"

    def get_context_data(self, **kwargs):
        """
        Adds an 'attributes' list to the request context consisting of the
        attributes specified at the class level, and in the order provided.

        Django views do not provide a way to reference dynamic attributes, so
        we have to grab them all before we render the template.

        Returns:
            context (dict): Django context object

        """
        # Get the base Django context object
        context = super().get_context_data(**kwargs)

        # Get the object in question
        obj = self.get_object()

        # Create an ordered dictionary to contain the attribute map
        # attribute_list = OrderedDict()

        # for attribute in self.attributes:
        #     # Check if the attribute is a core fieldname (name, desc)
        #     if attribute in self.typeclass._meta._property_names:
        #         attribute_list[attribute.title()] = getattr(obj, attribute, "")

        #     # Check if the attribute is a db attribute (char1.db.favorite_color)
        #     else:
        #         attribute_list[attribute.title()] = getattr(obj.db, attribute, "")

        # # Add our attribute map to the Django request context, so it gets
        # # displayed on the template
        # context["attribute_list"] = attribute_list

        webdesc = obj.db.desc if obj.db.desc else "This character has not provided a description."
        webdesc = _SPACE_RE.sub(' ', webdesc)
        webdesc = _TAB_RE.sub(' ', webdesc)
        webdesc = split_on_all_newlines(webdesc)

        context['webdesc'] = webdesc

        context['player_name'] = obj.player_name if obj.player_name else "~Unknown~"

        # Return the comprehensive context object
        return context



    def get_queryset(self):
        """
        This method will override the Django get_queryset method to return a
        list of all characters the user may access.

        Returns:
            queryset (QuerySet): Django queryset for use in the given view.

        """
        account = self.request.user

        # Return a queryset consisting of characters the user is allowed to
        # see.
        ids = [
            obj.id for obj in self.typeclass.objects.all() if obj.access(account, self.access_type)
        ]

        return self.typeclass.objects.filter(id__in=ids).order_by(Lower("db_key"))