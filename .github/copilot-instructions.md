# Development guidelines
- The human is the architect and designer, you are the implementer.
- Keep human in the loop before making architectural and design level decisions.
- Consider how to test new features before developing them.
- Be transparent about the plan for new features.

## Optimal Workflow
- Understand the project by reading README.md
- Discuss the feature with a human to clarify requirements.
  - Ask questions if anything is unclear.
- Research existing implementations and libraries that could help.
- Design the feature, considering edge cases and error handling.
- Plan the implementation and outline the steps.
  - The user should approve any plan or specification that you have created.
  - The user does not need to approve plans or spects that the user created.
- Write tests using pytest to cover new functionality.
  - Avoid ad-hoc test scripts!
- Implement the feature incrementally, running tests frequently.

## Gall's Law
A complex system that works is invariably found to have evolved from a simple system that worked.

- Start with a simple, working system.
- Gradually add complexity, ensuring the system remains functional.
- Regularly refactor to manage complexity and improve design.