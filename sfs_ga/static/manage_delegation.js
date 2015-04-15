

$(document).ready(function () {
    $("input.votes_input").on('change', recalc_vote_dist);
    $(".adjust_vote_button").on('click', adjust_vote_dist);
    $("form#manage_delegation_votes").on('submit', submit_delegation_votes);
    recalc_vote_dist();
});

function recalc_vote_dist(event) {
    try { event.preventDefault(); } catch(e) {};
    var count = 0;
    $('input.votes_input').each( function() {
        count = count + parseInt($(this).val());
    });
    $('#distributed_votes').html(count);
    var total_votes = parseInt($('#total_votes').html());
    if (total_votes < count) {
        $('#distributed_votes').css('color', 'red');
    }
    if (total_votes == count) {
        $('#distributed_votes').css('color', 'green');
    }
    if (total_votes > count) {
        $('#distributed_votes').css('color', 'orange');
    }
}

function adjust_vote_dist(event) {
    event.preventDefault();
    var field = $(this).parents('td').find('.votes_input');
    var vote_count = parseInt(field.val());
    if ($(this).hasClass('plus_vote')) {
        //Assume plus
        vote_count = vote_count + 1;
    } else {
        //Assume minus
        if (vote_count == 0) {
            return false;
        }
        vote_count = vote_count - 1;
    }
    field.val(vote_count);
    field.change();
}

function submit_delegation_votes(event) {
    var total_votes = parseInt($('#total_votes').html());
    var distributed_votes = parseInt($('#distributed_votes').html());
    if (total_votes != distributed_votes) {
        event.preventDefault();
        arche.create_flash_message("Distribute all votes", {type: 'danger', auto_destruct: true});
        return false;
    }    
}
