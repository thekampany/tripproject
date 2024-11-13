document.addEventListener("DOMContentLoaded", function() {
    const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    
    fetch("/set_timezone/", {  
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({ timezone: userTimezone })
    }).then(response => {
        if (response.ok) {
            console.log("Timezone set successfully:", userTimezone);
        } else {
            console.error("Failed to set timezone.");
        }
    });
});
