importScripts("https://cdn.jsdelivr.net/pyodide/v0.25.1/full/pyodide.js");

let pyodide;

// Post status updates to main thread
function postStatus(message) {
    postMessage({ status: "loading", message });
}

async function initPyodide() {
    try {
        postStatus("Initializing Pyodide...");
        pyodide = await loadPyodide();
        console.log("✅ Pyodide initialized");

        postStatus("Installing micropip...");
        await pyodide.loadPackage(["micropip"]);
        console.log("✅ micropip loaded");

        postStatus("Installing LangGraph (this may take a moment)...");
        await pyodide.runPythonAsync(`
import micropip
await micropip.install("langgraph")
        `);
        console.log("✅ LangGraph installed");

        // Fetch agent.py and write it to Pyodide's virtual filesystem
        postStatus("Loading agent module...");
        const agentCode = await fetch("agent.py").then(r => r.text());
        pyodide.FS.writeFile("/home/pyodide/agent.py", agentCode);
        console.log("✅ agent.py loaded to virtual FS");

        // Add path for imports
        pyodide.runPython(`
import sys
sys.path.insert(0, '/home/pyodide')
        `);

        // Expose async-compatible call_llm using Pyodide's fetch wrapper
        // This JS function will be called from Python
        const callLlmAsync = async (prompt) => {
            const res = await fetch("http://localhost:8000/llm", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ prompt: prompt })
            });
            const data = await res.json();
            return data.text;
        };

        // Set the async function in Python globals
        pyodide.globals.set("js_call_llm", callLlmAsync);
        console.log("✅ js_call_llm function injected");

        // Create a Python wrapper that properly handles the async JS call
        await pyodide.runPythonAsync(`
import js
from pyodide.ffi import to_js

# Wrapper that calls the JS function and awaits the promise
def call_llm(prompt):
    """
    Call the backend LLM API via JavaScript.
    Uses synchronous XMLHttpRequest for compatibility with LangGraph.
    """
    try:
        # Use synchronous XMLHttpRequest via JavaScript
        from js import XMLHttpRequest
        xhr = XMLHttpRequest.new()
        xhr.open("POST", "http://localhost:8000/llm", False)  # False = synchronous
        xhr.setRequestHeader("Content-Type", "application/json")
        
        import json
        xhr.send(json.dumps({"prompt": prompt}))
        
        if xhr.status == 200:
            response = json.loads(xhr.responseText)
            return response.get("text", "No response")
        else:
            return f"Error: HTTP {xhr.status}"
    except Exception as e:
        return f"Error calling LLM: {str(e)}"

print("✅ call_llm wrapper created")
        `);

        // Import the agent module
        await pyodide.runPythonAsync(`
from agent import run_graph
print("✅ agent module imported successfully")
        `);
        console.log("✅ Agent module ready");

        postMessage({ status: "ready" });
    } catch (error) {
        console.error("❌ Initialization error:", error);
        postMessage({ error: `Initialization failed: ${error.message}` });
    }
}

onmessage = async (event) => {
    if (!pyodide) {
        postMessage({ error: "Pyodide not initialized yet" });
        return;
    }

    const userMessage = event.data;
    console.log("📨 Received message:", userMessage);

    try {
        // Escape the user message for Python string
        const escapedMessage = userMessage
            .replace(/\\/g, '\\\\')
            .replace(/"""/g, '\\"\\"\\"')
            .replace(/\n/g, '\\n');

        const result = await pyodide.runPythonAsync(`
run_graph("""${escapedMessage}""")
        `);

        console.log("📤 Result:", result);
        postMessage({ result: result });
    } catch (error) {
        console.error("❌ Execution error:", error);
        postMessage({ error: `Agent error: ${error.message}` });
    }
};

// Start initialization
initPyodide();
