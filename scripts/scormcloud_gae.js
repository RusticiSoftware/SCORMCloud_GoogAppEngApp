
$(document).ready(function(){
	
	$('div.coursebox-title').click(function(){
		$(this).toggleClass('active').next('div.coursebox-content').slideToggle();
		
	});
	
	$('div.coursebox-content.closed').hide();
	
	$('[hover]').hover(function(){$(this).addClass($(this).attr('hover'));},function(){$(this).removeClass($(this).attr('hover'));});
	$('[linkurl]').click(function(){window.location = $(this).attr('linkurl');});
	
	$('.togglebtn').click(function(){
		toggleDiv = $(this).siblings('.togglediv');
		if (toggleDiv.hasClass('off')){
			$(this).text($(this).attr('ontxt'));
			toggleDiv.removeClass('off');
			toggleDiv.slideDown();
		} else {
			$(this).text($(this).attr('offtxt'));
			toggleDiv.addClass('off');
			toggleDiv.slideUp();
		}
		
	});

	$('span.localizeDate').each(function(){
		var d = new Date($(this).attr('utcdate'));
		d.setTime(d.getTime() - (d.getTimezoneOffset() * 60000));
		var now = new Date();
		
		var fmt = $(this).attr('format');
		if(fmt != null){
			$(this).text(dateFormat(d, fmt));
		} else {
			$(this).text(d.toLocaleDateString() + " " + d.toLocaleTimeString());
		}
	});
	
	$('span.localizeRecentDate').each(function(){
		var d = new Date(jQuery(this).attr('utcdate'));
        d.setTime(d.getTime() - (d.getTimezoneOffset() * 60000));
        var now = new Date();

        jQuery(this).text(((now.getDate() == d.getDate()) ? "Today " : "Yesterday ") + "at " + d.toLocaleTimeString());
    });

	$('[corners]').each(function(){
		var radius = $(this).attr('corners');
		$(this).css('-webkit-border-radius', radius + 'px').css('-moz-border-radius', radius + 'px').css('border-radius', radius + 'px');
	});
	
	$(".messagebox .cancelmsg").click(function(){
		$(this).parent().fadeOut('slow');
		var key = $(this).attr('key');
		$.post("/ajax/removemessage/" + key,function(data){
				if (data.responseText == "success"){
					$(this).parent().remove();
				}});
		
	});
	
	$('.viewtraininghistory').click(function(){
		link = $(this);
		var senddata = {};
		if ($(this).hasClass('reg')){
			regid = link.attr('key');
			senddata.regid = regid;
		} else if ($(this).hasClass('course')){
			courseid = link.attr('key');
			senddata.courseid = courseid;
		} else if ($(this).hasClass('user')){
			userid = link.attr('key');
			senddata.userid = userid;
		}
		

		$.ajax({
			type:"POST",
			url: "/ajax/reporturl",
			data: senddata,
			complete: function(data){
				//alert(data.responseText);
				window.open(data.responseText);
			},
			dataType:"json"});
		
		return false;
		
	});
	
	
});

function ShowActionStatus(message){
	actDiv = $('#actionstatus');
	actDiv.text(message).css("left", ( $(window).width() - actDiv.width() ) / 2+$(window).scrollLeft() + "px").show();
}
function HideActionStatus(){
	$('#actionstatus').hide();
}


function MakeModalDialog(html){
	var newDiv = $('.messageDialog').clone();
	newDiv.html(html).dialog({modal:true
								,buttons: {
									Ok: function() {$(this).dialog('close').remove();}
								}
							});
}