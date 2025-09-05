from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from app.models import User, Post
from app import db

admin = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(view):
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            flash("Access denied: admin only.", "danger")
            return redirect(url_for('main.home'))
        return view(*args, **kwargs)
    wrapped.__name__ = view.__name__
    return wrapped


@admin.route('/dashboard')
@admin_required
def dashboard():
    users_count = User.query.count()
    posts_count = Post.query.count()
    flagged_count = Post.query.filter_by(status='flagged').count()
    return render_template('admin/dashboard.html',
                           users_count=users_count,
                           posts_count=posts_count,
                           flagged_count=flagged_count)


@admin.route('/users')
@admin_required
def users():
    q = request.args.get('q', '').strip()
    query = User.query
    if q:
        query = query.filter((User.username.ilike(
            f'%{q}%')) | (User.email.ilike(f'%{q}%')))
    users = query.order_by(User.id.desc()).all()
    return render_template('admin/users.html', users=users, q=q)


@admin.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot change your own admin status.", "warning")
        return redirect(url_for('admin.users'))
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f"Updated admin status for {user.username}.", "success")
    return redirect(url_for('admin.users'))


@admin.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot delete yourself.", "warning")
        return redirect(url_for('admin.users'))
    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "success")
    return redirect(url_for('admin.users'))


@admin.route('/posts')
@admin_required
def posts():
    status = request.args.get('status', 'all')
    query = Post.query
    if status != 'all':
        query = query.filter_by(status=status)
    posts = query.order_by(Post.date_posted.desc()).all()
    return render_template('admin/posts.html', posts=posts, status=status)


@admin.route('/posts/<int:post_id>/delete', methods=['POST'])
@admin_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash("Post deleted.", "success")
    return redirect(url_for('admin.posts'))


@admin.route('/posts/<int:post_id>/status', methods=['POST'])
@admin_required
def change_post_status(post_id):
    post = Post.query.get_or_404(post_id)
    new_status = request.form.get('status', 'published')
    post.status = new_status
    db.session.commit()
    flash("Post status updated.", "success")
    return redirect(url_for('admin.posts'))
