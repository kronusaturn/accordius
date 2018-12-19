from datetime import date, datetime
from django.db import models
from django.contrib.auth.models import User


# Create your models here.

class Profile(models.Model):
    user = models.ForeignKey(User, related_name="profile", on_delete=models.CASCADE)
    display_name = models.CharField(null=True, max_length=40)
    karma = models.IntegerField(default=1)
    last_notifications_check = models.DateTimeField(default=datetime.today)
    moderator = models.BooleanField(default=False)

class Post(models.Model):
    """A post object.

    - id: A 17 character truncated base64-encoded md5 hash.
    - posted_at: The time at which the post was made available, as opposed
    to draft creation.
    - frontpage_date: The time at which the post was put "on the front page",
    whatever that means in our software.
    - curated_date: The time at which the post was featured or put in the really
    good section, whatever that means in our software.
    - user: The author of the post as a user object.
    - title: The post's title.
    - url: A url that's submitted to create a link post, NOT the url of the post
    on the software instance's website.
    - base_score: The score of the post.
    - comment_count: The number of comments on the post.
    - view_count: How many views the post has gotten since it was published.
    - draft: Whether the post is a draft or not."""
    class Meta:
        ordering = ['-posted_at']
    id = models.CharField(primary_key=True, max_length=17)
    posted_at = models.DateTimeField(default=datetime.today)
    frontpage_date = models.DateTimeField(null=True, default=None)
    curated_date = models.DateTimeField(null=True, default=None)
    user = models.ForeignKey(User, related_name="posts",
                             null=True, on_delete=models.SET_NULL)
    title = models.CharField(default="Untitled (this should never appear)",
                             max_length=250)
    url = models.URLField(null=True)
    slug = models.CharField(max_length=60)
    base_score = models.IntegerField(default=1)
    body = models.TextField()
    vote_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    draft = models.BooleanField(default=True)

class Comment(models.Model):
    """A comment on a Post. 

    - id: A 17 character truncated base64-encoded md5 hash.
    - user: A user object representing the comments author
    - post: The post object on which the comment was made.
    - parent_comment: If this comment is a reply to another, this field
    is the comment object representing it. 
    - posted_at: The time at which the comment was posted.
    - base_score: The score of the comment object.
    - body: A markdown text comment body.
    - is_deleted: Whether the post has been hidden from public consumption."""
    id = models.CharField(primary_key=True, max_length=17)
    user = models.ForeignKey(User, related_name="comments",
                             null=True, on_delete=models.SET_NULL)
    post = models.ForeignKey(Post, related_name="comments",
                             null=True, on_delete=models.SET_NULL)
    parent_comment = models.ForeignKey('Comment',
                                       null=True, on_delete=models.SET_NULL)
    posted_at = models.DateTimeField(default=datetime.today)
    base_score = models.IntegerField(default=1)
    body = models.TextField()
    is_deleted = models.BooleanField(default=False)

class Tag(models.Model):
    """A tag on a post, comment, or other taggable item.

    - user: The user object that made the tag.
    - document_id: The id of the media that was tagged.
    - type: The type of media that was tagged.
    - created_at: The date on which the tag was made.
    - text: The tag text, which is case sensitive on storage but searched casei
    """
    user = models.ForeignKey(User, related_name="tags",
                             null=True, on_delete=models.SET_NULL)
    document_id = models.CharField(max_length=17)
    # Not an arbitrary limit, think about using type strings in code
    # They need to be able to fit onto a line with other code on it.
    type = models.CharField(max_length=40)
    created_at = models.DateTimeField(default=datetime.today)
    # Length-Limited by views
    text = models.TextField(unique=True)
    
class Vote(models.Model):
    """A vote on a post, comment, or other votable item.

    - user: The user object that made the vote.
    - voted_at: The date on which the vote was made.
    - power: The number of points the vote is worth, defaults to 1
    - vote_type: Whether the vote is an upvote or a downvote"""
    user = models.ForeignKey(User, related_name="votes", on_delete=models.CASCADE)
    document_id = models.CharField(max_length=17)
    voted_at = models.DateTimeField(default=datetime.today)
    vote_type = models.CharField(default="smallUpvote", max_length=25)
    power = models.IntegerField(default=1)

class Notification(models.Model):
    class Meta:
        ordering = ['-created_at']
    user = models.ForeignKey(User, related_name="notifications",
                             on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=datetime.today)
    document_id = models.CharField(max_length=17)
    document_type = models.CharField(max_length=50)
    type = models.CharField(max_length=50)
    message = models.TextField()
    viewed = models.BooleanField(default=False)
    
class Conversation(models.Model):
    created_at = models.DateTimeField(default=datetime.today)
    title = models.CharField(max_length=150)

class Participant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    conversation = models.ForeignKey(Conversation,
                                     related_name="participants",
                                     on_delete=models.CASCADE)
    
class Message(models.Model):
    user = models.ForeignKey(User,
                             null=True, on_delete=models.SET_NULL)
    conversation = models.ForeignKey(Conversation, related_name="messages",
                                     on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=datetime.today)
    body = models.TextField()
    
class Ban(models.Model):
    """This is referred to as a 'disinvite' in the interface. Defines a ban on
    a user.

    - user: The user that has been banned
    - created_at: The date and time of the ban
    - reason: The reason for the ban, as displayed in mod log
    - ban_message: The message displayed to the ban user when they try to log in
    - until: On what date they are considered unbanned
    - appeal_on: On what date the user is allowed to send a message to mods 
    appealing their ban"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=datetime.today)
    reason = models.CharField(max_length=2048)
    ban_message = models.CharField(max_length=2048)
    until = models.DateTimeField()
    appeal_on = models.DateTimeField()
