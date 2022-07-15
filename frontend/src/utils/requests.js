const get = (url, cache = 'no-cache') => {
    return new Promise((resolve, reject) => {
        fetch(url, {
            headers: {
                "Content-Type": "application/json",
                //   "Authorization": `Bearer ${token}`,
                // cache: cache, #  not allowed in preflight cors response.... idk
            },
        })
            .then(async res => {
                resolve(res.json())

            }).catch(err => {
                console.log(err)
                reject(err)
            })
    })
}


const post = (url, data) => {
    return new Promise((resolve, reject) => {
        fetch(url, {
            method: "POST",
            mode: "cors",
            // cache: "no-cache",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                //   "Authorization": `Bearer ${token}`,
            },
            redirect: "follow",
            refferrerPolicy: "no-referrer",
            body: JSON.stringify(data)
        })
            .then(async (res) => {

                if (res.status === 403) {
                    // console.log("403 but client should see error", errorData)
                    resolve("403 brooooo")
                } else {
                    // Normal request
                    resolve(res.json())
                }
            })
            .catch(err => {
                console.log(err)
                reject(err)
            })

    })
}

export { get, post }