from django.shortcuts import render
from django.views import View
from django.http import HttpResponse
from django.utils.datastructures import MultiValueDictKeyError
from rest_framework import viewsets, filters, generics
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.decorators import action
from lw2.models import *
from lw2.serializers import *
import lw2.search as wl_search
import datetime
import json
import h_annot # TODO: Modularize this out as some kind of extension


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """The API doesn't actually communicate with a users browser, so CSRF 
    doesn't make sense."""
    def enforce_csrf(self, request):
        return

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer

class PostViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows posts to be viewed or edited.
    """
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)
    queryset = Post.objects.all()
    serializer_class = PostSerializer

    # TODO: Convert this to use a custom permission class
    @action(detail=True, methods=['get', 'post'])
    def update_tagset(self, request, pk=None):
        """Replace the current set of tags on a post with the tags specified in 
        a comma separated list given by the client.

        Parameters:

        tags: A comma separated list of tags to update the post set to. 
        No commas or semicolons."""
        if request.method == 'GET':
            try:
                post = Post.objects.get(id=pk)
            except:
                return HttpResponse("No post with id {}".format(pk),
                                    status=404)
            tagstring = ','.join(
                [tag.text for tag in Tag.objects.filter(document_id=pk)]
            )
            return HttpResponse(JSONRenderer().render(tagstring),
                                content_type="application/json")
        # Try to detect bad update strings and errors before we delete the tags
        if (";" in request.POST["tags"]):
            return HttpResponse("Semicolons are not allowed in the update string.",
                                status=400)
        if '' in request.POST["tags"].split(","):
            return HttpResponse(
                """You've repeated a comma in your update string, implying you're 
                allowing commas in tags. Commas are not allowed to appear in a 
                tag string.""",
                status=400)
        try:
            post = Post.objects.get(id=pk)
        except:
            return HttpResponse("No post with id {}".format(pk),
                                status=404)
        # It'd be quite the bug if you could delete the tags on someone else's
        # post
        if post.user != request.user:
            return HttpResponse(
                "User {} is not the author of this post ({})".format(request.user.username,
                                                                     post.user.username),
                status=403)
        tags = Tag.objects.filter(document_id=pk).delete()
        for new_tag_text in request.POST["tags"].split(","):
            new_tag = Tag(user=request.user,
                          document_id=pk,
                          type="post",
                          created_at = datetime.datetime.now(),
                          text=new_tag_text)
            new_tag.full_clean()
            new_tag.save()
        return HttpResponse("Tags updated")
    
class CommentViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows comments to be viewed or edited.
    """
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)
    # Figure out later perhaps if there's a better way to ensure deleted content
    # can't be retrieved
    # TODO: Make deleted comments more foolproof
    queryset = Comment.objects.filter(is_deleted=False)
    serializer_class = CommentSerializer
    
    def destroy(self, request, pk=None):
        comment = self.queryset.get(id=pk)
        if comment.user != request.user:
            raise ValueError("Only a comments author can delete their comment")
        comment.is_deleted = True
        comment.save()
        return HttpResponse("Comment deleted")
    
class TagViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows tags to be viewed or edited.
    """
    authentication_classes = (CsrfExemptSessionAuthentication,BasicAuthentication)
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    filter_fields = ('user','document_id','text',)
        
class VoteViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows votes to be viewed or edited.
    """
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)
    queryset = Vote.objects.all()
    serializer_class = VoteSerializer

    
#TODO: Add API endpoint here that returns tag validation regex    
    
class BanViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows bans to be viewed or edited.
    """
    permission_classes = (DjangoModelPermissions,)
    queryset = Ban.objects.all()
    serializer_class = BanSerializer

class InviteViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows invites to be created or viewed.
    """
    permission_classes = (IsAuthenticated,)
    queryset = Invite.objects.all()
    serializer_class = InviteSerializer

class InviteList(viewsets.ViewSet):
    """
    API endpoint that lets a user get a list of their created invite codes.
    """
    
    def list(self, request):
        user = self.request.user
        invite_serializer = RestrictedInviteSerializer(Invite.objects.filter(creator=user),
                                                       context={'request': request}, many=True)
        if user.is_authenticated:
            return Response(invite_serializer.data)

# TODO: Refactor these to both inherit from one class or use same underlying method
# definition
class PostSearchView(viewsets.ViewSet):
    """Search posts with a query string ?query=

    See search.py for a quick guide to the search syntax rules."""
    def list(self, request):
        try:
            parsed_search = wl_search.parse_search_string(request.GET["query"])
        except MultiValueDictKeyError:
            raise ValueError("Didn't specify a query string. Use ?query=")
        filters = wl_search.mk_search_filters(parsed_search)
        posts = Post.objects.all()
        for _filter in filters:
            if _filter["exclude"]:
                posts = posts.exclude(_filter["Q"])
            else:
                posts = posts.filter(_filter["Q"])
        post_serializer = PostSerializer(posts, context={'request': request}, many=True)
        return HttpResponse(JSONRenderer().render(post_serializer.data),
                            content_type="application/json")
        
class CommentSearchView(viewsets.ViewSet):
    """Search comments with a query string ?query=

    See search.py for a quick guide to the search syntax rules."""
    def list(self, request):
        try:
            parsed_search = wl_search.parse_search_string(request.GET["query"])
        except MultiValueDictKeyError:
            raise ValueError("Didn't specify a query string. Use ?query=")
        filters = wl_search.mk_search_filters(parsed_search)
        comments = Comment.objects.all()
        for _filter in filters:
            if _filter["exclude"]:
                comments = comments.exclude(_filter["Q"])
            else:
                comments = comments.filter(_filter["Q"])
        comment_serializer = CommentSerializer(comments,
                                               context={'request': request},
                                               many=True)
        return HttpResponse(JSONRenderer().render(comment_serializer.data),
                            content_type="application/json")

class AnnotationList(viewsets.ViewSet):
    """Get a list of hypothes.is annotations for a given user."""
    def list(self, request):
        try:
            user_id = request.GET["userid"]
        except KeyError:
            return HttpResponse(
                json.dumps(
                    {"code":"annotation_search_no_user",
                     "message":"No userid given to search.",
                     "blame":"client",
                     "retry":False}
                ),
                status=400,
                content_type="application/json"
            )
        try:
            limit = int(request.GET["limit"])
            if limit > 100:
                limit = 100
        except ValueError:
            try:
                limit = int(request.GET["limit"].split(".")[0])
            except:
                return HttpResponse(
                    json.dumps(
                        {"code":"annotation_search_limit_malformed",
                         "message":"The value '{}' is not an integer value.".format(
                             request.GET["limit"]),
                         "blame":"user",
                         "retry":False}),
                    status=400)
        except KeyError:
            limit = 10
        
        try:
            user = User.objects.get(id=user_id)       
        except User.DoesNotExist:
            return HttpResponse(
                json.dumps(
                    {"code":"annotation_search_user_not_found",
                     "message":"The user with ID '{}' does not exist.".format(user_id),
                     "blame":"client",
                     "retry":False}
                ),
                status=404
            )
        return HttpResponse(
            h_annot.api.search(user.profile.hypothesis_api_key,
                               user=user.profile.hypothesis_user,
                               group=user.profile.hypothesis_group,
                               limit=limit),
            content_type="application/json"
            )
