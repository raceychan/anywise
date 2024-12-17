import uvicorn

app_str = "anywise.demo.api:app_factory"
uvicorn.run(app_str, reload=True)
