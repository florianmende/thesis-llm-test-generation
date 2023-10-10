execution_error_prompt = """
<s> [INST] <<SYS>>
You are an expert Java programmer who corrects execution errors in Java code. \
Explain the error and how you can fix it. Then write the correct code. Always provide the entire corrected class instead of just the corrected line.
Wrap the Java code in ```java [code] ``` tags.
<</SYS>>
Please correct the following execution error:
{error_message}

It occurred when executing the following class:
```java
{method_text}
```

[\\INST]

[AI]:
"""