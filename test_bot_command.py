import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock class for message
class MockMessage:
    def __init__(self, text):
        self.text = text
    
    async def edit_text(self, text, *args, **kwargs):
        print(f"\n[EDITED MESSAGE OUTPUT]:\n{text.encode('ascii', 'backslashreplace').decode('ascii')}\n")
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
        print(f"\n[INITIAL REPLY]: {text.encode('ascii', 'backslashreplace').decode('ascii')}")
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

async def test_avci():
    print("\nTesting avci_command with mocked Update and Context...")
    from main import avci_command
    update = MockUpdate()
    context = MockContext()
    await avci_command(update, context)

if __name__ == "__main__":
    asyncio.run(test_avci())

