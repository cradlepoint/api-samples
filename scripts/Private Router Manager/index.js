function headerSelect(name) {
    document.getElementById("license").style.display = "none";
    document.getElementById("license button").style.backgroundColor = "";
    document.getElementById("ncos").style.display = "none";
    document.getElementById("ncos button").style.backgroundColor = "";
    document.getElementById("config").style.display = "none";
    document.getElementById("config button").style.backgroundColor = "";

    document.getElementById(name).style.display = "block";
    document.getElementById(name + " button").style.backgroundColor = "grey";
}

function trigger(action) {
    swal({title: 'Executing!', icon: "success", buttons: false, timer: 1500});
    var goData = new FormData();
    goData.append("go_" + action, null)
    $.ajax({
        url: '/',
        type: 'post',
        data: goData,
        contentType: false,
        processData: false,
        success: function (response) {
            if (response !== 0) {

            } else {
                swal({title: 'Error!', icon: "error", buttons: false, timer: 1500});
            }
        },
    });
}

$(document).ready(function() {
    $("form").submit(function() {
        event.preventDefault();
        var formData = new FormData();
        var name = $(this).attr('name')
        formData.append(name, this[0].files[0]);

        $.ajax({
            url: '/',
            type: 'post',
            data: formData,
            contentType: false,
            processData: false,
            success: function (response) {
                if (response !== 0) {
                    swal({title: 'File Uploaded!', icon: "success", buttons: false, timer: 1500});
                    document.getElementById(name + " action").style.display = "block";
                    if (name === "routers") {
                        let list = document.getElementById("routers_list");
                        list.title = "Routers"
                        let json = JSON.parse(response);
                        json.routers.forEach((item) => {
                            let li = document.createElement("li");
                            li.innerText = item;
                            list.appendChild(li);
                        });
                    }

                } else {
                    swal({title: 'Error During Upload!', icon: "error", buttons: false, timer: 1500});
                    document.getElementById(name + " action").style.display = "none";
                }
            },
        });
    })
});
