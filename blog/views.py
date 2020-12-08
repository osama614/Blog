from django.shortcuts import render, get_object_or_404
from .models import Post, Comment
from django.views.generic import ListView
from django.core.paginator import Paginator, EmptyPage,\
PageNotAnInteger

from .forms import EmailPostForm, CommentForm, SearchForm  
from django.core.mail import send_mail
from taggit.models import Tag
from django.db.models import Count
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
# Create your views here.

def post_list(request, tag_slug=None):
    posts = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        posts = posts.filter(tags__name__in=[tag])

    paginator = Paginator(posts, 2)
    page = request.GET.get('page')
    try:
      posts = paginator.page(page)
    except PageNotAnInteger:
    # If page is not an integer deliver the first page
      posts = paginator.page(1)
    except EmptyPage:
    # If page is out of range deliver last page of results
      posts = paginator.page(paginator.num_pages)


    return render(request,'blog/post/list.html',{'posts': posts, 'page': page, 'tag':tag})


def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post, slug=post, status='published', publish__year=year, publish__month=month, publish__day=day)
    comments = post.comments.filter(active=True)
    new_comment = None
    comment_form = CommentForm()
    if request.method == "POST":
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = post
            new_comment.save()

    post_tags_ids = post.tags.values_list('id', flat=True)   
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags')).order_by('-same_tags', '-publish')[:4]
    return render(request, 'blog/post/detail.html',{'post': post,
                                                     'comments': comments,
                                                     'new_comment': new_comment,
                                                     'comment_form': comment_form,
                                                     'similar_posts': similar_posts}
                                                     )    


# class PostListView(ListView):
#     queryset = Post.published.all()
#     context_object_name = 'posts'
#     paginate_by = 1
#     template_name = 'blog/post/list.html'    

def post_share(request, post_id):
# Retrieve post by id
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False
    if request.method == 'POST':
        # Form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # Form fields passed validation
            cd = form.cleaned_data
            # ... send email
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = f"{cd['name']} recommends you read " f"{post.title}"
            message = f"Read {post.title} at {post_url}\n\n" f"{cd['name']}\'s comments: {cd['comments']}"
            send_mail(subject, message, 'osamass9000@gmail.com',
            [cd['to']], fail_silently=False)
            sent = True

    else:
        form = EmailPostForm()
    return render(request, 'blog/post/share.html', {'post': post,'form': form, 'sent': sent})

def post_search(request):
  form = SearchForm()
  query = None
  results = []

  if 'query' in request.GET:
    form = SearchForm(request.GET)
    if form.is_valid():
      query = form.cleaned_data['query']
      search_query = SearchQuery(query)
      search_vector = SearchVector('body', 'title')

      results = Post.published.annotate(search =search_vector, rank=SearchRank(search_vector, search_query)).filter(search = search_query).order_by('-rank')

  return render(request, 'blog/post/search.html', {'form':form, 'query':query, 'results':results})