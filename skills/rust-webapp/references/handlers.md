# Route Handlers

## AppError Type

The template includes `AppError` for proper error handling. All handlers return `Result<T, AppError>`. The template's version maps every error to 500; when adding the first UPDATE/DELETE handler, replace it with this one so a missing row returns 404 (adding the variant earlier leaves it unused, which clippy rejects):

```rust
pub enum AppError {
    NotFound,
    Internal(anyhow::Error),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        match self {
            Self::NotFound => (StatusCode::NOT_FOUND, "Not found").into_response(),
            Self::Internal(err) => {
                tracing::error!("Application error: {err}");
                (StatusCode::INTERNAL_SERVER_ERROR, "Something went wrong").into_response()
            }
        }
    }
}

impl<E> From<E> for AppError
where
    E: Into<anyhow::Error>,
{
    fn from(err: E) -> Self {
        Self::Internal(err.into())
    }
}
```

## CRUD Handlers

All handlers use `?` operator - **never `.expect()` or `.unwrap()`**.

```rust
use axum::{
    extract::{State, Path, Form},
    response::{Html, Redirect, IntoResponse},
};
use askama::Template;

// LIST
async fn list_tasks(State(state): State<AppState>) -> Result<Html<String>, AppError> {
    let tasks = sqlx::query_as!(Task, "SELECT id, title, completed FROM tasks")
        .fetch_all(&state.pool)
        .await?;
    let template = IndexTemplate { tasks };
    Ok(Html(template.render()?))
}

// GET SINGLE
async fn get_task(
    State(state): State<AppState>,
    Path(id): Path<i32>,
) -> Result<Html<String>, AppError> {
    let task = sqlx::query_as!(Task, "SELECT id, title, completed FROM tasks WHERE id = $1", id)
        .fetch_optional(&state.pool)
        .await?
        .ok_or_else(|| anyhow::anyhow!("Task not found"))?;
    let template = EditTemplate { task };
    Ok(Html(template.render()?))
}

// CREATE
async fn create_task(
    State(state): State<AppState>,
    Form(input): Form<CreateTask>,
) -> Result<impl IntoResponse, AppError> {
    sqlx::query!("INSERT INTO tasks (title) VALUES ($1)", input.title)
        .execute(&state.pool)
        .await?;
    Ok(Redirect::to("/"))
}

// UPDATE
async fn update_task(
    State(state): State<AppState>,
    Path(id): Path<i32>,
    Form(input): Form<UpdateTask>,
) -> Result<impl IntoResponse, AppError> {
    let result = sqlx::query!(
        "UPDATE tasks SET title = COALESCE($1, title), completed = COALESCE($2, completed) WHERE id = $3",
        input.title,
        input.completed,
        id
    )
    .execute(&state.pool)
    .await?;

    if result.rows_affected() == 0 {
        return Err(AppError::NotFound);
    }
    Ok(Redirect::to("/"))
}

// DELETE (returns empty for HTMX to remove element)
async fn delete_task(
    State(state): State<AppState>,
    Path(id): Path<i32>,
) -> Result<Html<&'static str>, AppError> {
    let result = sqlx::query!("DELETE FROM tasks WHERE id = $1", id)
        .execute(&state.pool)
        .await?;

    if result.rows_affected() == 0 {
        return Err(AppError::NotFound);
    }
    Ok(Html(""))
}
```

## Router Setup

```rust
let app = Router::new()
    .route("/", get(list_tasks).post(create_task))
    .route("/new", get(new_form))
    .route("/{id}/edit", get(get_task))
    .route("/{id}", post(update_task).delete(delete_task))
    .nest_service("/static", ServeDir::new("static"))
    .with_state(state);
```

## Transactions

When multiple queries must succeed together, wrap them in a transaction - see [Pitfalls: Transactions for Atomic Operations](./pitfalls.md#transactions-for-atomic-operations).

## Error Inspection

Don't use `is_err()` blindly - inspect the actual error type. See [Pitfalls: Don't Use is_err() Blindly](./pitfalls.md#dont-use-is_err-blindly).
