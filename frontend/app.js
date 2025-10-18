document.addEventListener('DOMContentLoaded', () => {
    console.log('SACI Frontend App Loaded');

    initializeMaestrosView();
    initializeCreacionListaView();
    initializeRegistroTransaccionView();
    initializeReportesView();
});

const API_BASE_URL = '/api';

// --- Estado de la aplicación ---
let nuevaListaItems = [];
let productoSeleccionado = null;
let transaccionItems = [];

// --- Gestión de Maestros ---

async function initializeMaestrosView() {
    await Promise.all([
        fetchAndRenderProductos(),
        populateFilterOptions('categorias', 'categoria-filter'),
        populateFilterOptions('marcas', 'marca-filter')
    ]);

    document.getElementById('filter-btn').addEventListener('click', () => {
        const search = document.getElementById('search-input').value;
        const categoria = document.getElementById('categoria-filter').value;
        const marca = document.getElementById('marca-filter').value;
        fetchAndRenderProductos({ search, categoria, marca });
    });
}

async function populateFilterOptions(endpoint, elementId) {
    try {
        const response = await fetch(`${API_BASE_URL}/${endpoint}/`);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(
                `Error en la red: ${response.statusText} - ${JSON.stringify(
                    errorData
                )}`
            );
        }
        const items = await response.json();
        const select = document.getElementById(elementId);
        select.innerHTML = `<option value="">-- Todas las ${endpoint} --</option>`;
        items.forEach((item) => {
            const option = document.createElement("option");
            option.value = item.id;
            option.textContent = item.nombre;
            select.appendChild(option);
        });
    } catch (error) {
        console.error(`Error al poblar ${endpoint}:`, error);
    }
}

async function fetchAndRenderProductos(filters = {}) {
    const { search = "", categoria = "", marca = "" } = filters;
    const queryParams = new URLSearchParams({
        search,
        producto__categoria: categoria,
        marca,
    });

    try {
        const response = await fetch(
            `${API_BASE_URL}/productos-detalle/?${queryParams}`
        );
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(
                `Error en la red: ${response.statusText} - ${JSON.stringify(
                    errorData
                )}`
            );
        }
        const productos = await response.json();
        renderProductos(productos);
    } catch (error) {
        console.error("Error al obtener los productos:", error);
        document.getElementById("productos-list").innerHTML =
            "<p>No se pudieron cargar los productos.</p>";
    }
}

function renderProductos(productos) {
    const container = document.getElementById('productos-list');
    if (productos.length === 0) {
        container.innerHTML = '<p>No hay productos que coincidan con la búsqueda.</p>';
        return;
    }
    const table = document.createElement('table');
    table.className = 'productos-table';
    const thead = document.createElement('thead');
    thead.innerHTML = `<tr><th>Producto</th><th>Marca</th><th>Presentación</th><th>Categoría</th></tr>`;
    table.appendChild(thead);
    const tbody = document.createElement('tbody');
    productos.forEach(p => {
        const row = document.createElement('tr');
        row.innerHTML = `<td>${p.producto_nombre}</td><td>${p.marca_nombre}</td><td>${p.presentacion}</td><td>${p.categoria_nombre}</td>`;
        tbody.appendChild(row);
    });
    table.appendChild(tbody);
    container.innerHTML = '';
    container.appendChild(table);
}

// --- Creación de Listas ---

function initializeCreacionListaView() {
    const itemSearchInput = document.getElementById('item-search');
    const searchResultsContainer = document.getElementById('item-search-results');

    itemSearchInput.addEventListener('input', async (e) => {
        const searchTerm = e.target.value;
        if (searchTerm.length < 3) {
            searchResultsContainer.innerHTML = '';
            return;
        }
        const productos = await searchProductos(searchTerm);
        renderSearchResults(productos, searchResultsContainer, (producto) => {
            productoSeleccionado = producto;
            itemSearchInput.value = `${producto.producto_nombre} ${producto.marca_nombre}`;
        });
    });

    document.getElementById('add-item-btn').addEventListener('click', () => {
        const cantidad = document.getElementById('item-cantidad').value;
        const precio = document.getElementById('item-precio').value;

        if (!productoSeleccionado || !cantidad || !precio) {
            alert('Por favor, seleccione un producto y complete la cantidad y el precio.');
            return;
        }

        const nuevoItem = {
            producto_detalle: productoSeleccionado.id,
            producto_nombre: `${productoSeleccionado.producto_nombre} ${productoSeleccionado.marca_nombre}`,
            cantidad_planeada: parseInt(cantidad),
            precio_estimado_unitario: parseFloat(precio)
        };

        nuevaListaItems.push(nuevoItem);
        renderItemsLista();
        calcularTotalEstimado();

        document.getElementById('item-search').value = '';
        document.getElementById('item-cantidad').value = '';
        document.getElementById('item-precio').value = '';
        productoSeleccionado = null;
    });

    document.getElementById('save-lista-btn').addEventListener('click', async () => {
        const nombre = document.getElementById('lista-nombre').value;
        const fecha = document.getElementById('lista-fecha').value;

        if (!nombre || !fecha || nuevaListaItems.length === 0) {
            alert('Por favor, complete el nombre, la fecha y añada al menos un ítem.');
            return;
        }

        const listaData = {
            nombre: nombre,
            fecha_planeada: fecha,
            items: nuevaListaItems.map(item => ({
                producto_detalle: item.producto_detalle,
                cantidad_planeada: item.cantidad_planeada,
                precio_estimado_unitario: item.precio_estimado_unitario
            }))
        };

        try {
            const response = await fetch(`${API_BASE_URL}/listas-compra/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(listaData)
            });

            if (response.ok) {
                alert('¡Lista de compra guardada exitosamente!');
                // Limpiar todo
                document.getElementById('lista-nombre').value = '';
                document.getElementById('lista-fecha').value = '';
                nuevaListaItems = [];
                renderItemsLista();
                calcularTotalEstimado();
            } else {
                const errorData = await response.json();
                console.error('Error al guardar la lista:', errorData);
                alert('Hubo un error al guardar la lista.');
            }
        } catch (error) {
            console.error('Error de red:', error);
            alert('Hubo un error de red al intentar guardar la lista.');
        }
    });
}

function renderItemsNoPlaneados() {
    const container = document.getElementById('lista-items-no-planeados');
    container.innerHTML = '<h4>Ítems No Planeados Añadidos</h4>';
    const list = document.createElement('ul');
    itemsNoPlaneados.forEach(item => {
        const listItem = document.createElement('li');
        listItem.textContent = `${item.cantidad_real} x ${item.producto_nombre} @ ${item.precio_unitario_real.toFixed(2)}`;
        list.appendChild(listItem);
    });
    container.appendChild(list);
}

async function searchProductos(term) {
    try {
        const response = await fetch(`${API_BASE_URL}/productos-detalle/?search=${term}`);
        return await response.json();
    } catch (error) {
        console.error('Error en la búsqueda de productos:', error);
        return [];
    }
}

function renderSearchResults(productos, container, onSelectCallback) {
    container.innerHTML = '';
    const list = document.createElement('ul');
    productos.forEach(producto => {
        const listItem = document.createElement('li');
        listItem.textContent = `${producto.producto_nombre} ${producto.marca_nombre} - ${producto.presentacion}`;
        listItem.addEventListener('click', () => {
            onSelectCallback(producto);
            container.innerHTML = '';
        });
        list.appendChild(listItem);
    });
    container.appendChild(list);
}

function renderItemsLista() {
    const container = document.getElementById('items-lista-container');
    container.innerHTML = '';
    const list = document.createElement('ul');
    nuevaListaItems.forEach((item) => {
        const listItem = document.createElement('li');
        listItem.textContent = `${item.cantidad_planeada} x ${item.producto_nombre} @ ${item.precio_estimado_unitario.toFixed(2)}`;
        list.appendChild(listItem);
    });
    container.appendChild(list);
}

function calcularTotalEstimado() {
    const total = nuevaListaItems.reduce((sum, item) => sum + (item.cantidad_planeada * item.precio_estimado_unitario), 0);
    document.getElementById('total-estimado').textContent = total.toFixed(2);
}

// --- Reportes y Análisis ---

const charts = {};

function initializeReportesView() {
    populateReporteListaSelect();

    document.getElementById('reporte-lista-select').addEventListener('change', async (e) => {
        const listaId = e.target.value;
        if (!listaId) {
            document.getElementById('reporte-comparativo-container').innerHTML = '';
            return;
        }
        const response = await fetch(`${API_BASE_URL}/listas-compra/${listaId}/reporte-comparativo/`);
        const reporte = await response.json();
        renderReporteComparativo(reporte);
    });

    fetchReporteData('gasto_por_categoria', 'gasto-categoria-chart', 'Gasto por Categoría', 'pie');
    fetchReporteData('gasto_por_marca', 'gasto-marca-chart', 'Gasto por Marca', 'bar');

    const tendenciaSearchInput = document.getElementById('tendencia-search');
    const tendenciaSearchResults = document.getElementById('tendencia-search-results');

    tendenciaSearchInput.addEventListener('input', async (e) => {
        const searchTerm = e.target.value;
        if (searchTerm.length < 3) {
            tendenciaSearchResults.innerHTML = '';
            return;
        }
        const productos = await searchProductos(searchTerm);
        renderSearchResults(productos, tendenciaSearchResults, async (producto) => {
            tendenciaSearchInput.value = `${producto.producto_nombre} ${producto.marca_nombre}`;
            const response = await fetch(`${API_BASE_URL}/reportes/tendencia-precios/${producto.id}/`);
            const data = await response.json();
            const labels = data.map(d => d.lista_compra__fecha_ejecucion);
            const values = data.map(d => d.precio_unitario_real);
            renderChart('tendencia-precios-chart', 'Evolución de Precio', labels, values, 'line');
        });
    });
}

async function populateReporteListaSelect() {
    const response = await fetch(`${API_BASE_URL}/listas-compra/`);
    const listas = await response.json();
    const select = document.getElementById('reporte-lista-select');
    select.innerHTML = '<option value="">-- Seleccione una lista --</option>';
    listas.forEach(lista => {
        if (lista.fecha_ejecucion) { // Solo mostrar listas ejecutadas
            const option = document.createElement('option');
            option.value = lista.id;
            option.textContent = `${lista.nombre} (${lista.fecha_ejecucion})`;
            select.appendChild(option);
        }
    });
}

function renderReporteComparativo(reporte) {
    const container = document.getElementById('reporte-comparativo-container');
    const resumen = reporte.resumen;
    let html = `
        <h4>Resumen</h4>
        <p>Total Estimado: ${resumen.total_estimado}</p>
        <p>Total Real: ${resumen.total_real}</p>
        <p>Diferencia: ${resumen.diferencia_absoluta} (${resumen.diferencia_porcentual})</p>
        <h4>Detalle</h4>
    `;
    // Aquí se podría añadir una tabla con el detalle de los ítems
    container.innerHTML = html;
}

async function fetchReporteData(reporteTipo, chartId, label, chartType) {
    const response = await fetch(`${API_BASE_URL}/reportes/?reporte=${reporteTipo}`);
    const data = await response.json();
    const labels = data.map(d => d.nombre);
    const values = data.map(d => d.total_gastado);

    renderChart(chartId, label, labels, values, chartType);
}

function renderChart(chartId, label, labels, data, chartType) {
    const ctx = document.getElementById(chartId).getContext('2d');

    if (charts[chartId]) {
        charts[chartId].destroy();
    }

    charts[chartId] = new Chart(ctx, {
        type: chartType,
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: [
                    'rgba(255, 99, 132, 0.2)', 'rgba(54, 162, 235, 0.2)',
                    'rgba(255, 206, 86, 0.2)', 'rgba(75, 192, 192, 0.2)',
                    'rgba(153, 102, 255, 0.2)', 'rgba(255, 159, 64, 0.2)'
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)', 'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)', 'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)', 'rgba(255, 159, 64, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

// --- Registro de Transacciones ---

let itemsNoPlaneados = [];
let productoNoPlaneadoSeleccionado = null;

function initializeRegistroTransaccionView() {
    populateListasCompraSelect();

    const selectLista = document.getElementById('lista-a-registrar-select');
    selectLista.addEventListener('change', async (e) => {
        const listaId = e.target.value;
        if (!listaId) {
            document.getElementById('items-a-registrar-container').innerHTML = '';
            return;
        }
        try {
            const response = await fetch(`${API_BASE_URL}/listas-compra/${listaId}/`);
            const lista = await response.json();
            renderItemsParaRegistro(lista.items);
        } catch (error) {
            console.error('Error al obtener la lista:', error);
        }
    });

    const searchInputNoPlaneado = document.getElementById('item-search-no-planeado');
    const searchResultsNoPlaneado = document.getElementById('item-search-results-no-planeado');

    searchInputNoPlaneado.addEventListener('input', async (e) => {
        const searchTerm = e.target.value;
        if (searchTerm.length < 3) {
            searchResultsNoPlaneado.innerHTML = '';
            return;
        }
        const productos = await searchProductos(searchTerm);
        renderSearchResults(productos, searchResultsNoPlaneado, (producto) => {
            productoNoPlaneadoSeleccionado = producto;
            searchInputNoPlaneado.value = `${producto.producto_nombre} ${producto.marca_nombre}`;
        });
    });

    document.getElementById('add-item-no-planeado-btn').addEventListener('click', () => {
        const cantidad = document.getElementById('item-cantidad-no-planeado').value;
        const precio = document.getElementById('item-precio-no-planeado').value;

        if (!productoNoPlaneadoSeleccionado || !cantidad || !precio) {
            alert('Por favor, seleccione un producto y complete la cantidad y el precio.');
            return;
        }

        const nuevoItem = {
            item_lista_id: null,
            producto_detalle_id: productoNoPlaneadoSeleccionado.id,
            producto_nombre: `${productoNoPlaneadoSeleccionado.producto_nombre} ${productoNoPlaneadoSeleccionado.marca_nombre}`,
            cantidad_real: parseInt(cantidad),
            precio_unitario_real: parseFloat(precio)
        };

        itemsNoPlaneados.push(nuevoItem);
        renderItemsNoPlaneados();

        document.getElementById('item-search-no-planeado').value = '';
        document.getElementById('item-cantidad-no-planeado').value = '';
        document.getElementById('item-precio-no-planeado').value = '';
        productoNoPlaneadoSeleccionado = null;
    });

    document.getElementById('save-transaccion-btn').addEventListener('click', async () => {
        const listaId = selectLista.value;
        if (!listaId) {
            alert('Por favor, seleccione una lista de compra.');
            return;
        }

        const itemsPlaneadosData = Array.from(document.querySelectorAll('.item-a-registrar')).map(div => ({
            item_lista_id: parseInt(div.dataset.itemId),
            producto_detalle_id: parseInt(div.dataset.productoDetalleId),
            cantidad_real: parseInt(div.querySelector('.cantidad-real').value),
            precio_unitario_real: parseFloat(div.querySelector('.precio-real').value)
        }));

        const transaccionData = {
            items: [...itemsPlaneadosData, ...itemsNoPlaneados]
        };

        try {
            const response = await fetch(`${API_BASE_URL}/listas-compra/${listaId}/registrar-compra/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(transaccionData)
            });

            if (response.ok) {
                alert('¡Compra registrada exitosamente!');
                // Resetear vistas
                document.getElementById('items-a-registrar-container').innerHTML = '';
                itemsNoPlaneados = [];
                renderItemsNoPlaneados();
                populateListasCompraSelect();
            } else {
                const errorData = await response.json();
                console.error('Error al registrar la compra:', errorData);
                alert('Hubo un error al registrar la compra.');
            }
        } catch (error) {
            console.error('Error de red:', error);
            alert('Hubo un error de red al intentar registrar la compra.');
        }
    });
}

async function populateListasCompraSelect() {
    try {
        const response = await fetch(`${API_BASE_URL}/listas-compra/`);
        const listas = await response.json();
        const select = document.getElementById('lista-a-registrar-select');
        select.innerHTML = '<option value="">-- Seleccione una lista --</option>';
        listas.forEach(lista => {
            if (!lista.fecha_ejecucion) { // Solo mostrar listas no ejecutadas
                const option = document.createElement('option');
                option.value = lista.id;
                option.textContent = `${lista.nombre} (${lista.fecha_planeada})`;
                select.appendChild(option);
            }
        });
    } catch (error) {
        console.error('Error al poblar las listas de compra:', error);
    }
}

function renderItemsParaRegistro(items) {
    const container = document.getElementById('items-a-registrar-container');
    container.innerHTML = '<h3>Ítems Planeados</h3>';

    items.forEach(item => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'item-a-registrar';
        itemDiv.dataset.itemId = item.id;
        itemDiv.dataset.productoDetalleId = item.producto_detalle;

        itemDiv.innerHTML = `
            <span>${item.cantidad_planeada} x ${item.producto_nombre} (Estimado: ${item.precio_estimado_unitario})</span>
            <input type="number" class="cantidad-real" placeholder="Cant. Real" value="${item.cantidad_planeada}">
            <input type="number" class="precio-real" placeholder="Precio Real">
        `;
        container.appendChild(itemDiv);
    });

    // Lógica para ítems no planeados (simplificada para este ejemplo)
    const searchInputNoPlaneado = document.getElementById('item-search-no-planeado');
    const searchResultsNoPlaneado = document.getElementById('item-search-results-no-planeado');
    let productoNoPlaneadoSeleccionado = null;

    searchInputNoPlaneado.addEventListener('input', async (e) => {
        const searchTerm = e.target.value;
        if (searchTerm.length < 3) {
            searchResultsNoPlaneado.innerHTML = '';
            return;
        }
        const productos = await searchProductos(searchTerm);
        renderSearchResults(productos, searchResultsNoPlaneado);
        // Sobrescribir el handler de click para actualizar la variable correcta
        searchResultsNoPlaneado.querySelectorAll('li').forEach((li, index) => {
            li.addEventListener('click', () => {
                productoNoPlaneadoSeleccionado = productos[index];
                searchInputNoPlaneado.value = li.textContent;
                searchResultsNoPlaneado.innerHTML = '';
            });
        });
    });

    document.getElementById('add-item-no-planeado-btn').addEventListener('click', () => {
        // Lógica para añadir a una lista temporal de no planeados
    });

    document.getElementById('save-transaccion-btn').addEventListener('click', () => {
        // Lógica para guardar la transacción completa
    });
}