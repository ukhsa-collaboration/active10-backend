document.getElementById("unsubscribeButton").addEventListener("click", async () => {
    const email = document.getElementById("email").value;
    const name = "active10_mailing_list";
    if (!email) {
        alert("Please enter your email address.");
        return;
    }

    try {
        const response = await fetch("/v1/users/public/email_preferences/unsubscribe/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ email, name }),
        });

        const responseData = await response.json();

        if (response.ok) {
            document.getElementById("responseMessage").style.color = "green";
            document.getElementById("responseMessage").innerText = responseData.message;
        } else {
            let errorMessage = "An error occurred.";
            if (responseData.detail && Array.isArray(responseData.detail)) {
                errorMessage = responseData.detail.map((error) => error.msg).join(", ");
            } else if (responseData.detail) {
                errorMessage = responseData.detail;
            }
            document.getElementById("responseMessage").style.color = "red";
            document.getElementById("responseMessage").innerText = errorMessage;
        }

        document.getElementById("responseMessage").style.display = "block";
    } catch (error) {
        document.getElementById("responseMessage").style.color = "red";
        document.getElementById("responseMessage").innerText = "An error occurred. Please try again.";
        document.getElementById("responseMessage").style.display = "block";
    }
});