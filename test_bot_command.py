import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock class for message
class MockMessage:
    def __init__(self, text):
        self.text = text
    
    async def edit_text(self, text, *args, **kwargs):
        print(f"\n[EDITED MESSAGE OUTPUT]:\n{text}\n")
        return self

# Mock class for update
class MockUpdate:
    class MockEffectiveUser:
        name = "TestUser"
    
    class MockEffectiveChat:
        id = 12345
        
    def __init__(self):
        self.effective_user = self.MockEffectiveUser()
        self.effective_chat = self.MockEffectiveChat()
        self.message = self
        
    async def reply_text(self, text, *args, **kwargs):
        print(f"\n[INITIAL REPLY]: {text}")
        return MockMessage(text)

# Mock class for context
class MockContext:
    pass

async def test_gcross():
    print("Testing gcross_command with mocked Update and Context...")
    from main import gcross_command
    update = MockUpdate()
    context = MockContext()
    await gcross_command(update, context)

if __name__ == "__main__":
    asyncio.run(test_gcross())
