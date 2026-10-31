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

        // Preload Pyodide's built-in packages
        postStatus("Loading core packages...");
        await pyodide.loadPackage(["micropip", "ssl"]);
        console.log("✅ Core packages loaded");

        postStatus("Installing LangGraph (this may take a moment)...");


        // Create the call_llm function in Python and inject it into builtins
        // This makes it accessible from any imported module
        await pyodide.runPythonAsync(`
import builtins
from js import XMLHttpRequest
import json

def _call_llm(prompt):
    """
    Call the backend LLM API via JavaScript XMLHttpRequest.
    Uses synchronous request for compatibility with graph execution.
    """
    try:
        xhr = XMLHttpRequest.new()
        xhr.open("POST", "http://localhost:8000/llm", False)  # False = synchronous
        xhr.setRequestHeader("Content-Type", "application/json")
        xhr.send(json.dumps({"prompt": prompt}))
        
        if xhr.status == 200:
            response = json.loads(xhr.responseText)
            return response.get("text", "No response")
        else:
            return f"Error: HTTP {xhr.status}"
    except Exception as e:
        return f"Error calling LLM: {str(e)}"

# Inject into builtins so it's globally available everywhere
builtins.call_llm = _call_llm

print("✅ call_llm function injected into builtins")
        `);
        console.log("✅ call_llm function injected into builtins");

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
