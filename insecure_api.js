// Test JavaScript file for Code Review Agent
// Contains various security and quality issues

const express = require('express');
const app = express();

// Security Issue: Hardcoded secrets
const JWT_SECRET = "supersecret123";
const DB_PASSWORD = "admin";

// Security Issue: CORS misconfiguration
app.use((req, res, next) => {
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Headers", "*");
    next();
});

// Security Issue: No input validation
app.post('/api/users', (req, res) => {
    const { username, email, password } = req.body;
    
    // VULNERABILITY: No input sanitization
    const query = `INSERT INTO users (username, email, password) VALUES ('${username}', '${email}', '${password}')`;
    
    // Security Issue: Plain text password storage
    database.execute(query);
    
    res.json({ success: true });
});

// Security Issue: Path traversal vulnerability
app.get('/api/files/:filename', (req, res) => {
    const filename = req.params.filename;
    
    // VULNERABILITY: No path validation allows directory traversal
    const filePath = `./uploads/${filename}`;
    
    res.sendFile(filePath);
});

// Performance Issue: Synchronous operations
app.get('/api/process-data', (req, res) => {
    // PERFORMANCE: Blocking operation in request handler
    const data = processLargeDataSync();
    
    res.json(data);
});

function processLargeDataSync() {
    // Performance Issue: Inefficient algorithm
    let result = [];
    
    for (let i = 0; i < 100000; i++) {
        // PERFORMANCE: String concatenation in loop
        let str = "";
        for (let j = 0; j < 100; j++) {
            str += "data" + j;
        }
        result.push(str);
    }
    
    return result;
}

// Quality Issue: No error handling
app.get('/api/user/:id', (req, res) => {
    const userId = req.params.id;
    
    // QUALITY: No error handling for database operations
    const user = database.getUser(userId);
    
    res.json(user);
});

// Quality Issue: Callback hell
function fetchUserData(userId, callback) {
    database.getUser(userId, (err, user) => {
        if (err) return callback(err);
        
        database.getUserPosts(userId, (err, posts) => {
            if (err) return callback(err);
            
            database.getUserComments(userId, (err, comments) => {
                if (err) return callback(err);
                
                // QUALITY: Deeply nested callbacks
                callback(null, { user, posts, comments });
            });
        });
    });
}

// Security Issue: Information disclosure
app.use((err, req, res, next) => {
    console.error(err.stack);
    
    // SECURITY: Exposing internal error details
    res.status(500).json({
        error: err.message,
        stack: err.stack,
        query: req.query
    });
});

app.listen(3000, () => {
    console.log('Server running on port 3000');
});