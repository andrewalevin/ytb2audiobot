import { VOTAgent } from "@vot.js/node/utils/fetchAgent";
import { NeuroClient } from "@toil/neurojs";
import { writeFile } from "fs/promises";
import { join } from "path";

// Extract command-line arguments
const args = process.argv.slice(2);
const movieId = args[0];
const outputDir = args[1] || "."; // Default to env var or current directory
const language = args[2] || "en"; // Default to env var or "en"

if (!movieId) {
    console.error("🧬❌ Error: movieId is required.");
    process.exit(1);
}

// Initialize NeuroClient with VOTAgent
const client = new NeuroClient({
    fetchOpts: { dispatcher: new VOTAgent() },
});

// Data payload for summarization
const requestData = {
    url: `https://www.youtube.com/watch?v=${movieId}`,
    language,
    extraOpts: {},
};

// Function to wait for session completion
async function waitForSession(sessionId, maxRetries = 50, delayMs = 5000) {
    let attempt = 0;
    let previousChapters = [];
    let roundsBeforeCheck = 3;
    let lastResult = null;

    console.log("🧬🔄 Monitoring session progress...");

    while (attempt < maxRetries) {
        try {
            requestData.extraOpts.sessionId = sessionId;
            const result = await client.summarizeVideo(requestData);

            console.log(`🧬📋 Session Status: ${result.chapters ? result.chapters.length : 0} chapters detected`);
            lastResult = result;

            if (roundsBeforeCheck <= 0) {
                if (JSON.stringify(result.chapters) === JSON.stringify(previousChapters)) {
                    console.log("🧬⚠️ No new chapters detected. Stopping monitoring...");
                    break;
                }
            } else {
                roundsBeforeCheck--;
            }

            previousChapters = result.chapters;
            if (result.status === "done") return result;

        } catch (error) {
            console.error("🧬❌ Error during session monitoring:", error);
        }

        attempt++;
        await new Promise((resolve) => setTimeout(resolve, delayMs));
    }

    console.log("🧬🔚 Session monitoring completed.");
    return lastResult;
}

// Main function to handle video summarization
async function summarizeVideo() {
    try {
        console.log("🧬🚀 Starting video summarization...");
        const res = await client.summarizeVideo(requestData);

        if (!res.sessionId) throw new Error("No session ID received.");

        console.log(`🧬🎬 Session started: ${res.sessionId}`);
        const finalResult = await waitForSession(res.sessionId);

        if (!finalResult) {
            console.log("🧬⚠️ No chapters detected. Using the last known result.");
            return;
        }

        const filePath = join(outputDir, `${movieId}-summary.json`);
        await writeFile(filePath, JSON.stringify(finalResult, null, 2));

        console.log(`🧬✅ Summary saved: ${filePath}`);
    } catch (error) {
        console.error("🧬❌ Error during summarization:", error);
    }
}

// Handle graceful shutdown
process.on("SIGINT", () => {
    console.log("🧬🛑 Process interrupted (SIGINT). Exiting...");
    process.exit(0);
});
process.on("SIGTERM", () => {
    console.log("🧬🛑 Process terminated (SIGTERM). Exiting...");
    process.exit(0);
});

summarizeVideo();