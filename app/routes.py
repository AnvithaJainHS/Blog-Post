from email_validator import (  # You can install with 'pip install email-validator'
    EmailNotValidError,
    validate_email,
)
from flask import Flask, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash

from app import app, db
from app.models import Comment, Post, User


# Register new user
@app.route("/register", methods=["POST"])
def register_user():
    data = request.get_json()

    # Validate the incoming data
    if not data.get("username") or not data.get("email") or not data.get("password"):
        return jsonify(
            {"message": "Missing required fields: username, email, or password"}
        ), 400

    try:
        # Validate email format
        try:
            validate_email(data["email"])
        except EmailNotValidError as e:
            return jsonify({"message": f"Invalid email address: {str(e)}"}), 400

        # Check if the username already exists in the database
        if User.query.filter_by(username=data["username"]).first():
            return jsonify({"message": "Username already exists!"}), 400

        # Hash the password
        hashed_password = generate_password_hash(data["password"])

        # Create the new user and save to the database
        new_user = User(
            username=data["username"],
            email=data["email"],
            password_hash=hashed_password,
        )

        db.session.add(new_user)
        db.session.commit()  # Ensure that changes are committed to the database

        return jsonify({"message": "User created successfully!"}), 201

    except Exception as e:
        # Log the error and return an internal server error
        print(f"Error: {e}")
        db.session.rollback()  # Rollback in case of error to maintain a clean session
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500


# Login
@app.route("/login", methods=["POST"])
def login_user():
    # Ensure data exists
    if not request.is_json:
        return jsonify({"message": "Missing JSON in request"}), 400

    data = request.get_json()

    # Ensure the required fields are provided
    if not all(key in data for key in ["username", "password"]):
        return jsonify({"message": "Missing 'username' or 'password' field"}), 400

    # Find user by username
    user = User.query.filter_by(username=data["username"]).first()

    # If user is found and password matches
    if user and check_password_hash(user.password_hash, data["password"]):
        # Create access token for the user
        access_token = create_access_token(identity=str(user.id))
        return jsonify(access_token=access_token)

    # If the user is not found or password is incorrect
    return jsonify({"message": "Invalid credentials"}), 401


# Create Post
@app.route("/posts", methods=["POST"])
@jwt_required()
def create_post():
    data = request.get_json()

    # Check if 'title' and 'content' are in the request
    if not data.get("title") or not data.get("content"):
        return jsonify({"message": "Title and content are required!"}), 400

    current_user_id = get_jwt_identity()

    try:
        # Create the new post
        new_post = Post(
            title=data["title"], content=data["content"], author_id=current_user_id
        )

        # Add the post to the database and commit
        db.session.add(new_post)
        db.session.commit()

        return jsonify({"message": "Post created successfully!"}), 201

    except Exception as e:
        # If there is any error with the database, return a 500 Internal Server Error
        return jsonify({"message": "Error creating post", "error": str(e)}), 500


# Get all Posts
@app.route("/posts", methods=["GET"])
def get_posts():
    posts = Post.query.all()
    return jsonify(
        [
            {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "author": post.author.username,
                "created_at": post.created_at,
                "updated_at": post.updated_at,
            }
            for post in posts
        ]
    )


# Get single post
@app.route("/posts/<int:id>", methods=["GET"])
def get_post(id):
    # Retrieve the post by its ID
    post = Post.query.get(id)

    # Check if the post exists
    if post:
        # Return the post details as a JSON response
        return jsonify(
            {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "author": post.author.username,
                "created_at": post.created_at,
                "updated_at": post.updated_at,
            }
        )

    # If post doesn't exist, return an error message
    return jsonify({"message": "Post not found!"}), 404


# Update post
@app.route("/posts/<int:id>", methods=["PUT"])
@jwt_required()
def update_post(id):
    # Parse incoming data
    data = request.get_json()

    # Validate title and content
    title = data.get("title")
    content = data.get("content")

    if not title or not content:
        return jsonify({"message": "Title and content are required!"}), 400

    # Get the post by id
    post = Post.query.get(id)

    if not post:
        return jsonify({"message": "Post not found!"}), 404

    # Update the post fields
    post.title = title
    post.content = content

    try:
        # Commit the changes to the database
        db.session.commit()
        return jsonify(
            {
                "message": "Post updated successfully!",
                "post": {
                    "id": post.id,
                    "title": post.title,
                    "content": post.content,
                    "author": post.author.username,
                    "created_at": post.created_at,
                    "updated_at": post.updated_at,
                },
            }
        ), 200
    except Exception as e:
        # Handle any errors during the commit
        db.session.rollback()  # Rollback in case of error
        return jsonify({"message": "Error updating post", "error": str(e)}), 500


# Delete post
@app.route("/posts/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_post(id):
    # Get the post by id
    post = Post.query.get(id)

    if not post:
        return jsonify({"message": "Post not found!"}), 404

    # Delete the post
    db.session.delete(post)
    db.session.commit()

    return jsonify({"message": "Post deleted successfully!"}), 200


# Create Comment
@app.route("/comments", methods=["POST"])
@jwt_required()
def create_comment():
    data = request.get_json()
    current_user_id = get_jwt_identity()
    post = Post.query.get(data["post_id"])
    if not post:
        return jsonify({"message": "Post not found"}), 404
    new_comment = Comment(
        content=data["content"], post_id=data["post_id"], author_id=current_user_id
    )
    db.session.add(new_comment)
    db.session.commit()
    return jsonify({"message": "Comment created successfully!"}), 201


# Get comments for a post
@app.route("/comments", methods=["GET"])
def get_comments():
    post_id = request.args.get("post_id", type=int)

    if not post_id:
        return jsonify({"message": "Post ID is required"}), 400

    # Get the comments for the given post
    comments = Comment.query.filter_by(post_id=post_id).all()

    if not comments:
        return jsonify({"message": "No comments found for this post."}), 404

    return jsonify(
        [
            {
                "id": comment.id,
                "content": comment.content,
                "author": comment.author.username,
                "created_at": comment.created_at,
            }
            for comment in comments
        ]
    )


# Get single comment
@app.route("/comments/<int:id>", methods=["GET"])
def get_single_comment(id):
    # Get the comment by id
    comment = Comment.query.get(id)

    if not comment:
        return jsonify({"message": "Comment not found!"}), 404

    return jsonify(
        {
            "id": comment.id,
            "content": comment.content,
            "author": comment.author.username,
            "created_at": comment.created_at,
        }
    )


# Update comment
@app.route("/comments/<int:id>", methods=["PUT"])
@jwt_required()
def update_comment(id):
    data = request.get_json()

    # Get the comment by id
    comment = Comment.query.get(id)

    if not comment:
        return jsonify({"message": "Comment not found!"}), 404

    # Ensure the current user is the author of the comment
    current_user_id = get_jwt_identity()
    if comment.author_id != current_user_id:
        return jsonify(
            {"message": "You are not authorized to update this comment!"}
        ), 403

    # Update the comment content
    comment.content = data.get("content", comment.content)

    # Commit the changes to the database
    db.session.commit()

    return jsonify({"message": "Comment updated successfully!"}), 200


# Delete comment
@app.route("/comments/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_comment(id):
    # Get the comment by id
    comment = Comment.query.get(id)

    if not comment:
        return jsonify({"message": "Comment not found!"}), 404

    # Ensure the current user is the author of the comment
    current_user_id = get_jwt_identity()
    if comment.author_id != current_user_id:
        return jsonify(
            {"message": "You are not authorized to delete this comment!"}
        ), 403

    # Delete the comment
    db.session.delete(comment)
    db.session.commit()

    return jsonify({"message": "Comment deleted successfully!"}), 200
