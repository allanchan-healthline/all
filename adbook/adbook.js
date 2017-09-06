
///////////////////////////////////////////////////////////
// Index file
///////////////////////////////////////////////////////////

// Select a CM to refresh the campaign list
$("#select_cm").change(function(){
    var cm = this.value;
    var pacing = $("#select_pacing").val();

    $("div", "#main").hide();

    if ((cm == "all_cms") && (pacing == "all_pacing")) {
        $("div", "#main").slideToggle();
    } else if ((cm == "all_cms") && (pacing != "all_pacing")) {
        $("." + pacing).slideToggle();
    } else if ((cm != "all_cms") && (pacing == "all_pacing")) {
        $("." + cm).slideToggle();
    } else {
        $("." + cm + "." + pacing).slideToggle();
    }
});

// Select a pacing to refresh the campaign list
$("#select_pacing").change(function(){
    var cm = $("#select_cm").val();
    var pacing = this.value;

    $("div", "#main").hide();

    if ((cm == "all_cms") && (pacing == "all_pacing")) {
        $("div", "#main").slideToggle();
    } else if ((cm == "all_cms") && (pacing != "all_pacing")) {
        $("." + pacing).slideToggle();
    } else if ((cm != "all_cms") && (pacing == "all_pacing")) {
        $("." + cm).slideToggle();
    } else {
        $("." + cm + "." + pacing).slideToggle();
    }
});

///////////////////////////////////////////////////////////
// Campaign files
///////////////////////////////////////////////////////////

// Click on the Campaign header to show
// the Line Item tables and all of the columns
// If all are shown, then hide all

$("#camp_header").click(function(){

  function show_all() {
    $(".li_details").show();
    $(".li_col_site_size").show();
  };

  var showed_all = false;
  $(".li_details").each(function(index, value) {
    if ($(this).css("display") == "none") {
      show_all();
      showed_all = true;
      return;
    };
  });

  if (showed_all) {
    return;
  }

  $(".li_col_site_size").each(function(index, value) {
    if ($(this).css("display") == "none") {
      show_all();
      showed_all = true;
      return;
    };
  });

  if (showed_all) {
    return;
  }

  $(".li_details").hide();
  $(".li_col_site_size").hide();
});

// Click on the Line Item header to show/hide the table
// Only show site total columns
$(".li_header").click(function(){
    $details = $(this).next();
    $(".li_col_site_size", $details).hide();
    $details.slideToggle();
});

// Click on a site total column to show/hide that site's all columns
$(".li_col_site_total").click(function(){
    $table = $(this).parent().parent().parent();
    $classes = this.className.split(" ");
    for (var i=0; i < $classes.length; ++i) {
      if ($classes[i].startsWith("col_site_")) {
        $site = $classes[i];
        break;
      }
    }
    $(".li_col_site_size." + $site, $table).slideToggle();
});

// Click on a site's size column to hide that site's all columns
$(".li_col_site_size").click(function(){
    $table = $(this).parent().parent().parent();
    $classes = this.className.split(" ");
    for (var i=0; i < $classes.length; ++i) {
      if ($classes[i].startsWith("col_site_")) {
        $site = $classes[i];
        break;
      }
    }
    $(".li_col_site_size." + $site, $table).slideToggle();
});

// Click on non-site-specific columns (on the left) to show all columns
$(".li_col_all").click(function(){
    $table = $(this).parent().parent().parent();
    $(".li_col_site_size", $table).show();
});

///////////////////////////////////////////////////////////
// iframe index
///////////////////////////////////////////////////////////
$(document).ready(function(){
  if (window.name == "iframe_index") {
    $(document.body).addClass("in_iframe");
  }
});

$("#iframe_left_wrapper").resizable(); /* need jquery ui */

$('#iframe_left_wrapper').resize(function(){
   $('#iframe_right_wrapper').width($("#iframes_wrapper").width()-$("#iframe_left_wrapper").width());
});

$(window).resize(function(){
   $('#iframe_right_wrapper').width($("#iframes_wrapper").width()-$("#iframe_left_wrapper").width());
   $('#iframe_left_wrapper').height($("#iframes_wrapper").height());
});
