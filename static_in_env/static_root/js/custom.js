/**
 * Created by toruitas on 3/15/16.
 */


// Show Passed Flashed Message
function showFlashMessage(message){
    // template tags don't work in pure xxx.js, so have to copy it manually
    //var template = "{% include '_alert.html' with message='" + message + "'%}"; // renders this line as a string that turns into
    var template = "<div class='container container-alert-flash'>"+
                        "<div class='col-sm-3 col-sm-offset-8'>"+
                            "<div class='alert alert-success alert-dismissible' role='alert'>"+
                                "<button type='button' class='close' data-dismiss='alert' aria-label='Close'>"+
                                    "<span aria-hidden='true'>&times;</span>" +
                                "</button>"
                                +message+
                            "</div>" +
                        "</div>" +
                    "</div>";
    $("body").append(template);
    $('.container-alert-flash').fadeIn();
    setTimeout(function(){
        $('.container-alert-flash').fadeOut();
    },1800); // 1000ms = 1sec
}

function updateCartItemCount(){
        var badge = $("cart-count-badge");

        $.ajax({
            type:"GET",
            url:"{% url 'item_count' %}",
            success: function(data){
                badge.text(data.count);
                console.log(data.count);
            },
            error: function(response, data){
                console.log(response); //.responseText
                console.log(error);
            }
        })
    }

$(document).ready(function(){
    updateCartItemCount();
});