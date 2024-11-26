# # import sys
# from anywise import AnyWise, ICommand
# from dataclasses import dataclass

# @dataclass
# class SignupUser(ICommand):
#     user_name: str
#     user_email: str

# # Example handler class
# class UserService:
#     def handle_signup(self, command: SignupUser):
#         print(f"Signing up user: {command.user_name} ({command.user_email})")


# def test():
#     anywise = AnyWise()
    

#     # Register a class
#     anywise.register(UserService)
    
#     # Test sending a command
#     command = SignupUser(user_name="John", user_email="john@example.com")
#     anywise.send(command)

# if __name__ == "__main__":
#     test()