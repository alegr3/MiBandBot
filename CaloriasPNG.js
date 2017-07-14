var args = require('system').args;
var url = args[1];
var webpage = require('webpage').create();
//var url = "http://ec2-52-207-106-35.compute-1.amazonaws.com/app/kibana#/dashboard/Mi-Band-Dashboard?_g=(refreshInterval:(display:Off,pause:!f,value:0),time:(from:'2017-02-27T14:24:08.437Z',mode:quick,to:'2017-03-01T18:46:38.436Z'))&_a=(filters:!(),options:(darkTheme:!f),panels:!((col:1,id:Mi-Band-Pasos,panelIndex:1,row:9,size_x:12,size_y:4,type:visualization),(col:1,id:Mi-Band-Calorias,panelIndex:2,row:5,size_x:12,size_y:4,type:visualization),(col:1,id:Mi-Band-Actividad,panelIndex:3,row:1,size_x:12,size_y:4,type:visualization)),query:(query_string:(analyze_wildcard:!t,query:'*')),title:'Mi%20Band%20Dashboard',uiState:(P-1:(vis:(legendOpen:!f)),P-2:(vis:(legendOpen:!f)),P-3:(vis:(legendOpen:!f))))";

webpage.viewportSize = { width: 1150, height: 430 };
webpage.clipRect = { top: 0, left: 0, width: 1150, height: 450 };
webpage.open(url, function (status) {
             if (status !== 'success') {
             console.log('Unable to load the address!');
             phantom.exit();
             } else {
             window.setTimeout(function () {
                               webpage.evaluate(function() {
                                                var head = document.getElementsByTagName('head')[0];
                                                var style1 = document.createElement("style");
                                                style1.setAttribute("type","text/css");
                                                style1.innerHTML = '.gridster [data-col="4"] { left:183.5px; }.gridster [data-col="3"] { left:124px; }.gridster [data-col="2"] { left:64.5px; }.gridster [data-col="1"] { left:5px; }.gridster [data-row="4"] { top:335px; }.gridster [data-row="3"] { top:225px; }.gridster [data-row="2"] { top:115px; }.gridster [data-row="1"] { top:5px; }.gridster [data-sizey="1"] { height:100px; }.gridster [data-sizey="2"] { height:210px; }.gridster [data-sizey="3"] { height:320px; }.gridster [data-sizey="4"] { height:430px; }.gridster [data-sizex="1"] { width:49.5px; }.gridster [data-sizex="2"] { width:109px; }.gridster [data-sizex="3"] { width:168.5px; }.gridster [data-sizex="4"] { width:228px; }';
                                                head.appendChild(style1);
                                                //$('style')[5].remove()
                                                head.removeChild(document.getElementsByTagName('style')[5]);
                                                var visualize = $('visualize.panel-content.ng-scope.ng-isolate-scope')[1];
                                                var visContainer = $('div.vis-container')[0];
                                                var visualizeChart = $('div.visualize-chart')[1].outerHTML;
                                                visContainer.innerHTML = visualizeChart;
                                                visualize.innerHTML = visContainer.outerHTML;
                                                var panelHeading = document.getElementsByClassName('panel-heading')[1];
                                                var panelTitle = document.getElementsByClassName('panel-title ng-binding')[1].outerHTML;
                                                panelHeading.innerHTML = panelTitle;
                                                var divPanel = $('div.panel.panel-default.ng-scope')[0];
                                                divPanel.innerHTML = panelHeading.outerHTML + visualize.outerHTML;
                                                var dashboardPanel = document.createElement('dashboard-panel');
                                                dashboardPanel.innerHTML = divPanel.outerHTML;
                                                var li = $('li.ng-scope.gs-w')[1];
                                                li.innerHTML = dashboardPanel.outerHTML;
                                                var ul = document.createElement('ul');
                                                ul.setAttribute('class','gridster');
                                                ul.innerHTML = li.outerHTML;
                                                var dashboardGrid = $('dashboard-grid.ready')[0];
                                                dashboardGrid.innerHTML = ul.outerHTML;
                                                var body = document.getElementById('kibana-body');
                                                document.getElementsByTagName("body")[0].style.overflow = "hidden";
                                                document.getElementsByTagName("body")[0].style.height = "500px";
                                                document.getElementsByTagName("body")[0].style.maxHeight = "500px";
                                                body.innerHTML = dashboardGrid.outerHTML;
                                                html = document.createElement('html');
                                                document.getElementsByTagName("html")[0].style.overflow = "hidden";
                                                document.getElementsByTagName("html")[0].style.height = "500px";
                                                document.getElementsByTagName("html")[0].style.maxHeight = "500px";
                                                html.innerHTML = head.outerHTML + body.outerHTML;

                                                });
                                                webpage.render('Calorias.png', {format: 'png', quality: '50'});
                                                phantom.exit();
                               }, 12000); // Change timeout as required to allow sufficient time

             }

             });
