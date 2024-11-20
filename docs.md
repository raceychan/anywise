```c#
public class MyRequestHandler : IRequestHandler<MyRequest, MyResponse>
{
    public async Task<MyResponse> Handle(MyRequest request, CancellationToken cancellationToken)
    {
        // Handle the request
        return new MyResponse();
    }
}
```



```c#
public class CreateUserCommand : IRequest<int>
{
    public string UserName { get; set; }
    public string Email { get; set; }
}

// Implement a handler for the command
public class CreateUserCommandHandler : IRequestHandler<CreateUserCommand, int>
{
    public Task<int> Handle(CreateUserCommand request, CancellationToken cancellationToken)
    {
        // Business logic for creating a user
        // ...

        // Return the user ID or any relevant result
        return Task.FromResult(userId);
    }
}

// In your application code or controller
var createUserCommand = new CreateUserCommand { UserName = "JohnDoe", Email = "john@example.com" };
var userId = await mediator.Send(createUserCommand);
```

```c#
private readonly IMediator _mediator;

public OrdersController(IMediator mediator)
{
  _mediator = mediator;
}

[HttpGet]
public async Task<IActionResult> GetAllOrders()
{
  var query = new GetAllOrdersQuery();
  var result =await _mediator.Send(query);

  return Ok(result);
}
```

```py
we apply inversion of control to inversion of control to take our control back.

get_bus, set_bus = use_state(MessageBus)


@app.post("users")
async def create_user(command: Command):
    bus.handle(command)

bus.chain(router, Command) 
This would create the corresponding handler with router
we can also provides exceptions for router.

libname: stackless

checkout mediatr asp dotnet core
https://medium.com/@dev.esam2013/mediatr-and-cqrs-291ba0dc5dfe


EventHandler
middleware, where last middleware would publish it to queue
we can have

Form a chain of responsbility

Where parent_pre -> sub_pre -> hanlder -> sub_post -> parent_post

EventPipelinePre
    UserEventPipelinePre
       UserEventHandler
    UserEventPipelinePost
EventPipelineAfter
```