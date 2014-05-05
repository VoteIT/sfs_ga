$(document).ready(function () {
    $(".support_proposal_link").live('click', support_proposal);
    $(".show_supporters_popup").live('click', show_supporters_popup);
    $("#sort_on_support").live('click', sort_on_support);
    $("#sort_on_support_back").live('click', sort_on_support_back);
});

function sort_on_support(event) {
    try { event.preventDefault(); } catch(e) {};
    spinner().appendTo(this);
    var url = $(this).attr('href');
    $('#proposals .listing').load(url, function(response, status, xhr) {
        $('img.spinner').remove();
        $('#sort_on_support_back').show();
        $('#sort_on_support').hide();
        if (status == "error") {
            flash_message(voteit.translation['error_loading'], 'error', true);
        }
    });
}

function sort_on_support_back(event) {
    try { event.preventDefault(); } catch(e) {};
    spinner().appendTo(this);
    var url = $(this).attr('href');
    $.ajax({
           url: url,
        success: function(response) {
            $('#proposals .listing').html($('#proposals .listing', response).html());
            $('img.spinner').remove();
            $('#sort_on_support_back').hide();
            $('#sort_on_support').show();
        },
        error: function(response) {
            flash_message(voteit.translation['error_loading'], 'error', true);
            $('img.spinner').remove();
        }
    });

}

function support_proposal(event) {
    try { event.preventDefault(); } catch(e) {};
    spinner().appendTo(this);
    var url = $(this).attr('href');
    $(this).parents('.support_proposal').load(url, function(response, status, xhr) {
        $('img.spinner').remove();
        if (status == "error") {
            flash_message(voteit.translation['error_saving'], 'error', true);
        }
    });
}

function show_supporters_popup(event) {
    try { event.preventDefault(); } catch(e) {};
    var target = $(event.currentTarget);
    target.qtip({
        overwrite: false, // Make sure the tooltip won't be overridden once created
        content: { 
           title: {
                text: voteit.translation['supporters'],
                button: voteit.translation['close'],
            },
            text: voteit.translation['loading'], // The text to use whilst the AJAX request is loading
            ajax: { 
                url: target.attr('href'),
            },
        },
        show: {
            event: event.type, // Use the same show event as the one that triggered the event handler
            ready: true,
            effect: false,
        },
        hide: {
            event: "unfocus",
            effect: false,
        },
        position: {
            viewport: $(window),
            at: "bottom center",
            my: "top center",
            adjust: {
                method: 'shift none',
            },
        },
        style: { 
            classes: 'popup popup_dropshadow',
            widget: true,
            tip: true,
        },
    }, event);

}
