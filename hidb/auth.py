from __future__ import annotations

from datetime import datetime
import functools
import hmac
import secrets

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import abort
from werkzeug.security import check_password_hash, generate_password_hash

from hidb.models import db, User

bp = Blueprint("auth", __name__, url_prefix="/auth")

ROLE_OWNER = "owner"
ROLE_CO_OWNER = "co_owner"
ROLE_EDITOR = "editor"
ROLE_READER = "reader"
OWNER_ROLES = {ROLE_OWNER, ROLE_CO_OWNER}
VALID_ROLES = {ROLE_OWNER, ROLE_CO_OWNER, ROLE_EDITOR, ROLE_READER}
CSRF_SESSION_KEY = "_csrf_token"
PASSWORD_STAMP_SESSION_KEY = "password_updated_at"
LOGIN_ERROR = "Incorrect username or password."


def csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if token is None:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf():
    if not current_app.config.get("CSRF_ENABLED", True):
        return
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return

    token = session.get(CSRF_SESSION_KEY)
    submitted = request.form.get("_csrf_token") or request.headers.get(
        "X-CSRF-Token"
    )
    if not token or not submitted or not hmac.compare_digest(token, submitted):
        abort(400, "Invalid CSRF token.")


def password_stamp(user: User) -> str:
    if user.password_updated_at is None:
        return ""
    return user.password_updated_at.isoformat()


def min_password_length() -> int:
    return int(current_app.config.get("MIN_PASSWORD_LENGTH", 8))


def validate_password(password: str) -> str | None:
    if not password:
        return "Password is required."
    if len(password) < min_password_length():
        return f"Password must be at least {min_password_length()} characters."
    return None


def first_user_id() -> int | None:
    return db.session.query(func.min(User.id)).scalar()


def is_original_owner(user: User | None) -> bool:
    return user is not None and user.id == first_user_id()


def is_owner(user: User | None) -> bool:
    return user is not None and user.is_active and user.role == ROLE_OWNER


def is_co_owner(user: User | None) -> bool:
    return user is not None and user.is_active and user.role == ROLE_CO_OWNER


def is_owner_or_co_owner(user: User | None) -> bool:
    return user is not None and user.is_active and user.role in OWNER_ROLES


def is_editor(user: User | None) -> bool:
    return user is not None and user.is_active and user.role == ROLE_EDITOR


def _get(obj, key):
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def can_manage_users(actor: User | None) -> bool:
    return is_owner_or_co_owner(actor)


def can_create_place(actor: User | None) -> bool:
    return is_owner_or_co_owner(actor)


def can_manage_place(actor: User | None, place=None) -> bool:
    if not is_owner_or_co_owner(actor):
        return False
    if place is None:
        return True
    return can_view_place(actor, place)


def item_owner_id_for(actor: User | None) -> int | None:
    if actor is None or not actor.is_active:
        return None
    if actor.role in OWNER_ROLES:
        return actor.id
    if actor.role == ROLE_EDITOR:
        return actor.editor_for_id
    return None


def can_create_item(actor: User | None) -> bool:
    return item_owner_id_for(actor) is not None


def place_line_root_id(place) -> int:
    """User whose sponsorship line owns visibility for this place."""
    return _get(place, "creator_id")


def is_in_place_line(actor: User | None, line_root_id: int) -> bool:
    if actor is None or not actor.is_active:
        return False
    if actor.id == line_root_id:
        return True
    if is_editor(actor) and actor.editor_for_id == line_root_id:
        return True
    return False


def can_view_place(actor: User | None, place) -> bool:
    if actor is None or not actor.is_active:
        return False
    if is_owner(actor):
        return True
    if not _get(place, "is_private"):
        return True
    return is_in_place_line(actor, place_line_root_id(place))


def can_use_place_for_item(actor: User | None, place) -> bool:
    if not can_create_item(actor):
        return False
    return can_view_place(actor, place)


def can_edit_item(actor: User | None, item) -> bool:
    owner_id = item_owner_id_for(actor)
    return owner_id is not None and _get(item, "creator_id") == owner_id


def can_delete_item(actor: User | None, item) -> bool:
    return is_owner_or_co_owner(actor) and _get(item, "creator_id") == actor.id


def role_label(role: str | None) -> str:
    return {
        ROLE_OWNER: "Owner",
        ROLE_CO_OWNER: "Co-owner",
        ROLE_EDITOR: "Editor",
        ROLE_READER: "Reader",
    }.get(role, "Unknown")


def owner_sponsor_options():
    return (
        User.query.filter(User.role.in_(OWNER_ROLES), User.is_active.is_(True))
        .order_by(User.username)
        .all()
    )


def register_user(username: str, password: str) -> tuple[User | None, str | None]:
    role = ROLE_OWNER if User.query.count() == 0 else ROLE_READER

    try:
        user = User(
            username=username,
            password=generate_password_hash(password),
            role=role,
            is_active=True,
            password_updated_at=datetime.utcnow(),
        )
        db.session.add(user)
        db.session.commit()
        return user, None
    except IntegrityError:
        db.session.rollback()

    if User.query.filter_by(username=username).first() is not None:
        return None, f"User {username} is already registered."

    # A competing first-run registration may have claimed the immutable Owner.
    if role == ROLE_OWNER and User.query.filter_by(role=ROLE_OWNER).first():
        try:
            user = User(
                username=username,
                password=generate_password_hash(password),
                role=ROLE_READER,
                is_active=True,
                password_updated_at=datetime.utcnow(),
            )
            db.session.add(user)
            db.session.commit()
            return user, None
        except IntegrityError:
            db.session.rollback()

    return None, "Registration failed. Please try again."


def users_for_admin_list(actor: User | None):
    users = User.query.order_by(User.username).all()
    if is_owner(actor):
        return users
    if is_co_owner(actor):
        return [
            u
            for u in users
            if u.role == ROLE_READER
            or (u.role == ROLE_EDITOR and u.editor_for_id == actor.id)
        ]
    return []


def creatable_roles(actor: User | None):
    if is_owner(actor):
        return (ROLE_CO_OWNER, ROLE_EDITOR, ROLE_READER)
    if is_co_owner(actor):
        return (ROLE_EDITOR, ROLE_READER)
    return ()


def create_user_by_admin(
    actor: User,
    username: str,
    password: str,
    role: str,
    editor_for_id: int | None = None,
) -> tuple[User | None, str | None]:
    username = username.strip()
    if not username:
        return None, "Username is required."

    error = validate_password(password)
    if error is not None:
        return None, error

    if User.query.filter_by(username=username).first() is not None:
        return None, f"User {username} is already registered."

    sponsor_id = None
    if is_owner(actor):
        if role not in {ROLE_CO_OWNER, ROLE_EDITOR, ROLE_READER}:
            return None, "Invalid role."
        if role == ROLE_EDITOR:
            sponsor = User.query.get(editor_for_id)
            if not is_owner_or_co_owner(sponsor):
                return None, "Select an Owner or Co-owner for this Editor."
            sponsor_id = sponsor.id
    elif is_co_owner(actor):
        if role not in {ROLE_EDITOR, ROLE_READER}:
            return None, "Co-owners can only create Editors and Readers."
        sponsor_id = actor.id if role == ROLE_EDITOR else None
    else:
        return None, "Forbidden"

    user = User(
        username=username,
        password=generate_password_hash(password),
        role=role,
        editor_for_id=sponsor_id,
        is_active=True,
        password_updated_at=datetime.utcnow(),
        role_updated_at=datetime.utcnow(),
        role_updated_by_id=actor.id,
    )
    try:
        db.session.add(user)
        db.session.commit()
        return user, None
    except IntegrityError:
        db.session.rollback()
        return None, f"User {username} is already registered."


def apply_role_change(
    actor: User,
    target: User,
    new_role: str,
    editor_for_id: int | None,
) -> str | None:
    if new_role not in {ROLE_CO_OWNER, ROLE_EDITOR, ROLE_READER}:
        return "Invalid role."
    if is_original_owner(target):
        return "The original Owner cannot be changed."
    if not target.is_active:
        return "Disabled users cannot be promoted."

    if is_owner(actor):
        if new_role == ROLE_EDITOR:
            sponsor = User.query.get(editor_for_id)
            if not is_owner_or_co_owner(sponsor):
                return "Select an Owner or Co-owner for this Editor."
            target.editor_for_id = sponsor.id
        else:
            target.editor_for_id = None
    elif is_co_owner(actor):
        if new_role not in {ROLE_EDITOR, ROLE_READER}:
            return "Co-owners can only manage their own Editors."
        if target.role not in {ROLE_READER, ROLE_EDITOR}:
            return "Co-owners can only manage Readers and their own Editors."
        if target.role == ROLE_EDITOR and target.editor_for_id != actor.id:
            return "Co-owners can only manage their own Editors."
        target.editor_for_id = actor.id if new_role == ROLE_EDITOR else None
    else:
        abort(403)

    target.role = new_role
    target.role_updated_at = datetime.utcnow()
    target.role_updated_by_id = actor.id
    db.session.commit()
    return None


@bp.before_app_request
def protect_csrf():
    validate_csrf()


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
        return

    user = User.query.get(user_id)
    if (
        user is None
        or not user.is_active
        or session.get(PASSWORD_STAMP_SESSION_KEY) != password_stamp(user)
    ):
        session.clear()
        g.user = None
        return

    g.user = user


@bp.app_context_processor
def auth_template_helpers():
    return {
        "csrf_token": csrf_token,
        "can_create_item": can_create_item,
        "can_edit_item": can_edit_item,
        "can_delete_item": can_delete_item,
        "can_create_place": can_create_place,
        "can_manage_place": can_manage_place,
        "can_view_place": can_view_place,
        "can_manage_users": can_manage_users,
        "role_label": role_label,
    }


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        error = None

        if not username:
            error = "Username is required."
        else:
            error = validate_password(password)

        if error is None:
            _, error = register_user(username, password)
            if error is None:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template("auth/register.html.j2")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if (
            user is not None
            and user.is_active
            and check_password_hash(user.password, password)
        ):
            session.clear()
            session["user_id"] = user.id
            session[PASSWORD_STAMP_SESSION_KEY] = password_stamp(user)
            return redirect(url_for("items.index"))

        flash(LOGIN_ERROR)

    return render_template("auth/login.html.j2")


@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    return redirect(url_for("items.index"))


@bp.route("/users")
def users():
    if not can_manage_users(g.user):
        abort(403)
    return render_template(
        "auth/users.html.j2",
        users=users_for_admin_list(g.user),
        sponsor_options=owner_sponsor_options(),
        roles=(
            (ROLE_READER, ROLE_EDITOR, ROLE_CO_OWNER)
            if is_owner(g.user)
            else (ROLE_READER, ROLE_EDITOR)
        ),
        original_owner_id=first_user_id(),
    )


@bp.route("/users/create", methods=("GET", "POST"))
def create_user():
    if not can_manage_users(g.user):
        abort(403)

    roles = creatable_roles(g.user)
    sponsors = owner_sponsor_options() if is_owner(g.user) else []

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        role = request.form.get("role", ROLE_READER)
        sponsor_raw = request.form.get("editor_for_id", "")
        editor_for_id = int(sponsor_raw) if sponsor_raw else None

        error = None
        if password != confirm:
            error = "Passwords do not match."
        if error is None and role not in roles:
            error = "Invalid role."

        if error is None:
            _, error = create_user_by_admin(
                g.user, username, password, role, editor_for_id
            )

        if error is None:
            flash(f"Created user {username.strip()}.")
            return redirect(url_for("auth.users"))
        flash(error)

    return render_template(
        "auth/create_user.html.j2",
        roles=roles,
        sponsor_options=sponsors,
        default_role=ROLE_READER,
    )


@bp.route("/users/<int:user_id>/role", methods=("POST",))
def update_user_role(user_id):
    if not can_manage_users(g.user):
        abort(403)

    target = User.query.get_or_404(user_id)
    new_role = request.form.get("role", ROLE_READER)
    sponsor_raw = request.form.get("editor_for_id", "")
    editor_for_id = int(sponsor_raw) if sponsor_raw else None
    error = apply_role_change(g.user, target, new_role, editor_for_id)
    if error:
        flash(error)
    else:
        flash(f"Updated {target.username}.")
    return redirect(url_for("auth.users"))


@bp.route("/users/<int:user_id>/active", methods=("POST",))
def update_user_active(user_id):
    if not is_owner(g.user):
        abort(403)

    target = User.query.get_or_404(user_id)
    if is_original_owner(target):
        flash("The original Owner cannot be disabled.")
    else:
        target.is_active = request.form.get("is_active") == "1"
        if not target.is_active:
            target.editor_for_id = None
        target.role_updated_at = datetime.utcnow()
        target.role_updated_by_id = g.user.id
        db.session.commit()
        flash(f"Updated {target.username}.")
    return redirect(url_for("auth.users"))


@bp.route("/users/<int:user_id>/password", methods=("GET", "POST"))
def reset_user_password(user_id):
    if not is_owner(g.user):
        abort(403)

    target = User.query.get_or_404(user_id)
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        error = validate_password(password)
        if error is None and password != confirm:
            error = "Passwords do not match."

        if error is None:
            target.password = generate_password_hash(password)
            target.password_updated_at = datetime.utcnow()
            db.session.commit()
            flash(f"Password updated for {target.username}.")
            return redirect(url_for("auth.users"))
        flash(error)

    return render_template("auth/reset_password.html.j2", target=target)


@bp.route("/password", methods=("GET", "POST"))
def change_password():
    if g.user is None:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        error = None

        if not check_password_hash(g.user.password, current_password):
            error = "Current password is incorrect."
        else:
            error = validate_password(password)
        if error is None and password != confirm:
            error = "Passwords do not match."

        if error is None:
            g.user.password = generate_password_hash(password)
            g.user.password_updated_at = datetime.utcnow()
            db.session.commit()
            session[PASSWORD_STAMP_SESSION_KEY] = password_stamp(g.user)
            flash("Password updated.")
            return redirect(url_for("items.index"))
        flash(error)

    return render_template("auth/change_password.html.j2")


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view
