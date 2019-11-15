$(document).ready(function() {

    $('.modal').modal();
    $('.datepicker').datepicker({
    	format: 'dd-mm-yyyy'
    });

    $('.timepicker').timepicker({
    	twelveHour: false
    });
    $('select').formSelect();
 });
