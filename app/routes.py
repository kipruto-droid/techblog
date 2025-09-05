from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, current_app
from .models import Post, User, TrendingStory, Like, Profile, db
from flask_login import login_required, current_user
from .utils import save_upload
from .ai_agent import generate_summary
from werkzeug.utils import secure_filename
import os


main = Blueprint('main', __name__)


@main.route('/')
def home():
    # Get trending stories for carousel
    trending = TrendingStory.query.order_by(
        TrendingStory.date_posted.desc()).limit(10).all()

    posts = Post.query.order_by(
        Post.date_posted.desc()).all()  # fetch all newest first
    return render_template('home.html', posts=posts, trending=trending)


@main.route('/api/trending')
def get_trending():
    stories = TrendingStory.query.order_by(
        TrendingStory.published_at.desc()).limit(30).all()
    return jsonify([{
        "title": s.title,
        "description": s.description,
        "url": s.url,
        "image_url": s.image_url
    } for s in stories])


@main.route('/category/<string:category_name>')
def category(category_name):
    posts = Post.query.filter(Post.category.ilike(f'%{category_name}%')).order_by(
        Post.date_posted.desc()).all()
    return render_template('home.html', posts=posts, trending=[])


@main.route("/search")
def search():
    query = request.args.get('q')
    posts = Post.query.filter(Post.title.contains(query) | Post.summary.contains(query))\
                      .order_by(Post.date_posted.desc()).all()

    return render_template('home.html', posts=posts, search_query=query)


@main.route('/post/<int:post_id>')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post_detail.html', post=post)


@main.route('/dashboard')
@login_required
def dashboard():

    return render_template('dashboard.html', user=current_user)


@main.route('/blogs')
def blogs():
    posts = Post.query.order_by(Post.date_posted.desc()).all()
    return render_template('blogs.html', posts=posts)


@main.route('/about')
def about():
    return render_template('about.html')


# Contact page
@main.route('/contact')
def contact():
    return render_template('contact.html')


@main.route('/settings')
def settings():
    # You can render a settings page
    return render_template('settings.html')


# ----- VIEW PROFILE -----
@main.route("/profile/<username>")
@login_required
def profile_view(username):
    user = User.query.filter_by(username=username).first_or_404()
    # Ensure a profile exists
    if not user.profile:
        user.profile = Profile(user_id=user.id)
        db.session.add(user.profile)
        db.session.commit()
    return render_template("profile_view.html", user=user, profile=user.profile)

# ----- EDIT PROFILE -----


@main.route("/profile/edit", methods=["GET", "POST"])
@login_required
def profile_edit():
    # ensure a profile record
    if not current_user.profile:
        current_user.profile = Profile(user_id=current_user.id)
        db.session.add(current_user.profile)
        db.session.commit()

    if request.method == "POST":
        p = current_user.profile
        p.bio = request.form.get("bio") or p.bio
        p.tech_department = request.form.get(
            "tech_department") or p.tech_department
        p.skills = request.form.get("skills") or p.skills
        p.website = request.form.get("website") or p.website
        p.twitter = request.form.get("twitter") or p.twitter
        p.github = request.form.get("github") or p.github
        p.linkedin = request.form.get("linkedin") or p.linkedin

        avatar = request.files.get("avatar")
        if avatar:
            saved = save_upload(avatar, subfolder="avatars", kind="image")
            if saved:
                p.avatar_filename = saved
            else:
                flash(
                    "Avatar not saved (invalid type). Use png/jpg/webp/gif.", "warning")

        db.session.commit()
        flash("Profile updated!", "success")
        return redirect(url_for("main.profile_view", username=current_user.username))

    return render_template("profile_edit.html", user=current_user, profile=current_user.profile)

# ----- CREATE POST -----


@main.route("/post/create", methods=["GET", "POST"])
@login_required
def create_post():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        # optional, if your Post has it
        category = request.form.get("category", "").strip()

        if not title or not content:
            flash("Title and content are required.", "danger")
            return redirect(url_for("main.create_post"))

        image_file = request.files.get("image")
        video_file = request.files.get("video")

        image_path = save_upload(
            image_file, subfolder="posts", kind="image") if image_file else None
        video_path = save_upload(
            video_file, subfolder="posts", kind="video") if video_file else None

        # Optional AI summary (fallback to first 200 chars)
        summary = generate_summary(content) if content else (
            content[:200] if content else "")

        post = Post(
            title=title,
            content=content,
            summary=summary if summary else None,
            image_url=image_path,
            video_url=video_path,
            category=category if category else "General",
            user_id=current_user.id,
            status="published"
        )
        db.session.add(post)
        db.session.commit()
        flash("Post created!", "success")
        return redirect(url_for("main.post_detail", post_id=post.id))

    return render_template("create_post.html")

# ----- LIKE/UNLIKE -----


@main.route("/post/<int:post_id>/like", methods=["POST"])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    existing = Like.query.filter_by(
        user_id=current_user.id, post_id=post.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"status": "unliked", "likes": Like.query.filter_by(post_id=post.id).count()})
    else:
        like = Like(user_id=current_user.id, post_id=post.id)
        db.session.add(like)
        db.session.commit()
        return jsonify({"status": "liked", "likes": Like.query.filter_by(post_id=post.id).count()})


def save_upload(file, subfolder="posts", kind="file"):
    if not file or file.filename == "":
        return None

    filename = secure_filename(file.filename)
    upload_folder = os.path.join(
        current_app.root_path, "static", "uploads", subfolder)

    # Create folder if not exists
    os.makedirs(upload_folder, exist_ok=True)

    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)

    # return relative path for database
    return f"uploads/{subfolder}/{filename}"
